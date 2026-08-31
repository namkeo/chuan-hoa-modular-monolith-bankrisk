"""End-to-end orchestration of the bank-system risk analysis.

``run_pipeline`` ties together ingestion -> feature engineering -> validation ->
rule engine -> Isolation Forest -> K-means -> risk scoring -> high-risk periods ->
performance logging, and returns a single ``AnalysisResult`` consumed by the
Streamlit app and the reporting module. Results are cached on disk (parquet) keyed
by the data-folder signature + frequency so re-runs are fast.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .anomaly_detection import run_isolation_forest
from .clustering import latest_snapshot, run_kmeans
from .data_loader import LoadResult, load_all
from .ews import compute_ews
from .feature_engineering import build_features, compute_systemic_stress
from .feedback import false_positive_stats
from .performance_tracker import (StageTimer, build_run_record, log_run)
from .risk_scoring import bank_level_summary, compute_risk_scores
from .rule_engine import evaluate_rules, summarize_by_bank_period
from .stress_test import run_stress_test
from .time_series_analysis import (high_risk_periods_by_bank,
                                   identify_high_risk_periods)
from .utils import DATA_ROOT, LOG, PROCESSED_DIR, effective_model_config, load_config
from .validation import run_all_validation


@dataclass
class AnalysisResult:
    """Everything one analysis run produces, for one frequency."""
    frequency: str
    load: LoadResult
    features: pd.DataFrame = field(default_factory=pd.DataFrame)
    base_metrics: list[str] = field(default_factory=list)
    validation: pd.DataFrame = field(default_factory=pd.DataFrame)
    rule_findings: pd.DataFrame = field(default_factory=pd.DataFrame)
    rule_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    anomalies: pd.DataFrame = field(default_factory=pd.DataFrame)
    anomaly_features: list[str] = field(default_factory=list)
    cluster_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    cluster_profiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    cluster_projection: pd.DataFrame = field(default_factory=pd.DataFrame)
    cluster_k: int = 0
    cluster_metrics: dict = field(default_factory=dict)
    systemic_stress: pd.DataFrame = field(default_factory=pd.DataFrame)
    risk_scores: pd.DataFrame = field(default_factory=pd.DataFrame)
    bank_ranking: pd.DataFrame = field(default_factory=pd.DataFrame)
    high_risk_periods: pd.DataFrame = field(default_factory=pd.DataFrame)
    high_risk_by_bank: pd.DataFrame = field(default_factory=pd.DataFrame)
    ews_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    ews_latest: pd.DataFrame = field(default_factory=pd.DataFrame)
    ews_system: pd.DataFrame = field(default_factory=pd.DataFrame)
    ews_emerging: pd.DataFrame = field(default_factory=pd.DataFrame)
    ews_metrics: list[str] = field(default_factory=list)
    stress_results: pd.DataFrame = field(default_factory=pd.DataFrame)
    stress_system: pd.DataFrame = field(default_factory=pd.DataFrame)
    stress_breaking: pd.DataFrame = field(default_factory=pd.DataFrame)
    stress_scenarios: list[dict] = field(default_factory=list)
    stress_snapshot: str | None = None
    combined_source_map: dict = field(default_factory=dict)
    combined_meta: dict = field(default_factory=dict)
    timings: dict = field(default_factory=dict)
    runtime_sec: float = 0.0


def run_pipeline(folder: Path | str, frequency: str = "quarterly",
                 use_cache: bool = True, save_models: bool = False,
                 progress=None) -> AnalysisResult:
    """Run the full analysis for one frequency. ``progress`` is callable(frac, msg)."""
    folder = Path(folder)
    cfg = effective_model_config()      # model_config + applied tuned hyperparameters
    timer = StageTimer()

    def step(frac, msg):
        LOG.info(msg)
        if progress:
            progress(frac, msg)

    # ---- 1. Ingestion ----
    step(0.05, "Đọc & chuẩn hóa dữ liệu")
    with timer.stage("ingestion"):
        load = load_all(folder, use_cache=use_cache,
                        progress=(lambda f, m: progress(0.05 + 0.15 * f, m)) if progress else None)
    if load.panel.empty or frequency not in load.wide:
        LOG.warning("No data for frequency '%s'", frequency)
        return AnalysisResult(frequency=frequency, load=load)

    # ---- 2. Feature engineering ----
    step(0.25, "Tính chỉ tiêu / feature engineering")
    with timer.stage("features"):
        features = build_features(load.wide[frequency], frequency)
    base_metrics = features.attrs.get("base_metrics", [])

    # Capture cross-frequency provenance for the combined view.
    combined_source_map: dict = {}
    combined_meta: dict = {}
    if frequency == "combined":
        cw = load.wide.get("combined")
        if cw is not None:
            combined_source_map = cw.attrs.get("source_map", {})
            combined_meta = {"base_frequency": cw.attrs.get("base_frequency"),
                             "enriched_from": cw.attrs.get("enriched_from", [])}

    # ---- 3. Validation ----
    step(0.35, "Kiểm tra chất lượng dữ liệu")
    with timer.stage("validation"):
        validation = run_all_validation(load.panel, features)

    # ---- 4. Rule engine ----
    step(0.45, "Áp dụng hệ thống rule pháp lý")
    with timer.stage("rules"):
        rule_findings = evaluate_rules(features)
        rule_summary = summarize_by_bank_period(rule_findings)

    # ---- 5. Isolation Forest ----
    step(0.6, "Phát hiện bất thường (Isolation Forest)")
    with timer.stage("anomaly"):
        an = run_isolation_forest(features, base_metrics, cfg,
                                  save_as=frequency if save_models else None)

    # ---- 6. K-means ----
    step(0.7, "Phân cụm rủi ro (K-means)")
    with timer.stage("clustering"):
        snap = latest_snapshot(features)
        cl = run_kmeans(snap, base_metrics, cfg)

    # ---- 7. Systemic stress + risk scoring ----
    step(0.8, "Chấm điểm rủi ro tổng hợp")
    with timer.stage("scoring"):
        systemic = compute_systemic_stress(features)
        scores = compute_risk_scores(features, rule_findings, an.table, cl.table,
                                     validation, systemic, cfg)
        ranking = bank_level_summary(scores)

    # ---- 8. High-risk periods ----
    step(0.88, "Xác định giai đoạn rủi ro cao")
    with timer.stage("high_risk_periods"):
        hrp = identify_high_risk_periods(features, rule_findings, an.table, systemic, cfg)
        hrp_bank = high_risk_periods_by_bank(features, rule_findings, an.table)

    # ---- 8b. Early Warning System (leading indicators) ----
    step(0.92, "Hệ thống cảnh báo sớm (EWS)")
    with timer.stage("ews"):
        ews = compute_ews(features, frequency, an.table)

    # ---- 8c. Stress testing (scenario resilience) ----
    step(0.95, "Kiểm tra sức chịu đựng (stress test)")
    with timer.stage("stress"):
        stress = run_stress_test(features, frequency)

    runtime = timer.total

    # ---- 9. Performance log ----
    with timer.stage("perf_log"):
        fp = false_positive_stats()
        rec = build_run_record(
            panel=load.panel, features=features, frequency=frequency,
            anomaly_table=an.table, rule_findings=rule_findings, cluster_result=cl,
            validation_findings=validation, feedback_fp_rate=fp.get("overall_fp_rate"),
            runtime_sec=runtime, data_version=_data_signature(folder))
        try:
            log_run(rec)
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Could not write performance log: %s", exc)

    step(1.0, "Hoàn tất phân tích")
    return AnalysisResult(
        frequency=frequency, load=load, features=features, base_metrics=base_metrics,
        validation=validation, rule_findings=rule_findings, rule_summary=rule_summary,
        anomalies=an.table, anomaly_features=an.feature_names,
        cluster_table=cl.table, cluster_profiles=cl.profiles,
        cluster_projection=cl.projection, cluster_k=cl.k, cluster_metrics=cl.metrics,
        systemic_stress=systemic, risk_scores=scores, bank_ranking=ranking,
        high_risk_periods=hrp, high_risk_by_bank=hrp_bank,
        ews_table=ews.table, ews_latest=ews.latest, ews_system=ews.system,
        ews_emerging=ews.emerging, ews_metrics=ews.metrics_used,
        stress_results=stress.results, stress_system=stress.system,
        stress_breaking=stress.breaking_points, stress_scenarios=stress.scenarios,
        stress_snapshot=stress.snapshot_period,
        combined_source_map=combined_source_map, combined_meta=combined_meta,
        timings=timer.timings, runtime_sec=runtime)


def _data_signature(folder: Path) -> str:
    from .data_loader import _folder_signature, scan_data_files
    try:
        return _folder_signature(scan_data_files(folder))
    except Exception:  # noqa: BLE001
        return "n/a"


def available_frequencies(folder: Path | str) -> list[str]:
    """Frequencies the data folder yields. 'combined' (multi-frequency) leads when present."""
    load = load_all(Path(folder), use_cache=True)
    order = ["combined", "monthly", "quarterly", "yearly", "daily"]
    return [f for f in order if f in load.wide and not load.wide[f].empty]


if __name__ == "__main__":
    import sys
    freq = sys.argv[1] if len(sys.argv) > 1 else "quarterly"
    res = run_pipeline(DATA_ROOT, freq)
    print(f"\n=== Pipeline [{freq}] in {res.runtime_sec}s ===")
    print(f"Banks: {res.features['bank_id'].nunique() if not res.features.empty else 0}")
    print(f"Rule findings: {len(res.rule_findings)} | Anomalies flagged: "
          f"{int(res.anomalies['anomaly_label'].sum()) if not res.anomalies.empty else 0}")
    print(f"K-means k={res.cluster_k}")
    if not res.bank_ranking.empty:
        print("\nTop 10 risk banks:")
        print(res.bank_ranking[["bank_id", "period", "final_risk_score",
                                "risk_level"]].head(10).to_string(index=False))
    if not res.high_risk_periods.empty:
        hr = res.high_risk_periods[res.high_risk_periods["is_high_risk"]]
        print(f"\nHigh-risk periods: {len(hr)}")
        print(hr[["period", "period_risk_score", "reason"]].tail(6).to_string(index=False))
