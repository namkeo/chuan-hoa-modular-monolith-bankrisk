"""Performance & run tracking for the analysis pipeline.

Records one row per pipeline run into ``outputs/exports/performance_log.csv`` with
volumes, timings, model quality metrics, severity counts and version stamps. The
Performance dashboard page reads this log to show trends across runs.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from .utils import EXPORTS_DIR, LOG, load_config

PERF_LOG = EXPORTS_DIR / "performance_log.csv"

PERF_COLUMNS = [
    "run_ts", "n_records_panel", "n_banks", "n_periods", "frequency",
    "runtime_sec", "anomaly_rate_pct", "n_critical", "n_high", "n_medium",
    "n_data_gap", "silhouette", "kmeans_k", "missing_data_pct",
    "validation_error_rate", "feedback_fp_rate", "model_version",
    "data_version", "config_version",
]


@dataclass
class StageTimer:
    """Accumulates per-stage wall-clock timings within a run."""
    timings: dict = field(default_factory=dict)
    _start: float = field(default_factory=time.perf_counter)

    @contextmanager
    def stage(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.timings[name] = round(time.perf_counter() - t0, 3)
            LOG.info("Stage '%s' took %.3fs", name, self.timings[name])

    @property
    def total(self) -> float:
        return round(time.perf_counter() - self._start, 3)


def _versions() -> dict:
    cfg = load_config("model_config").get("versions", {})
    return {
        "model_version": cfg.get("model_version", "n/a"),
        "config_version": cfg.get("config_version", "n/a"),
    }


def build_run_record(
    *,
    panel: pd.DataFrame,
    features: pd.DataFrame,
    frequency: str,
    anomaly_table: pd.DataFrame | None,
    rule_findings: pd.DataFrame | None,
    cluster_result=None,
    validation_findings: pd.DataFrame | None = None,
    feedback_fp_rate: float | None = None,
    runtime_sec: float | None = None,
    data_version: str | None = None,
) -> dict:
    """Assemble a single performance-log record from pipeline outputs."""
    rec = {c: None for c in PERF_COLUMNS}
    rec["run_ts"] = datetime.now().isoformat(timespec="seconds")
    rec["frequency"] = frequency
    rec["n_records_panel"] = int(len(panel)) if panel is not None else 0
    if features is not None and not features.empty:
        rec["n_banks"] = int(features["bank_id"].nunique())
        rec["n_periods"] = int(features["period"].nunique())
        id_cols = {"bank_id", "bank_name", "period", "period_ts"}
        val_cols = [c for c in features.columns if c not in id_cols]
        if val_cols:
            rec["missing_data_pct"] = round(features[val_cols].isna().mean().mean() * 100, 2)
    if anomaly_table is not None and not anomaly_table.empty and "anomaly_label" in anomaly_table.columns:
        rec["anomaly_rate_pct"] = round(float(anomaly_table["anomaly_label"].mean()) * 100, 2)
    if rule_findings is not None and not rule_findings.empty:
        vc = rule_findings["severity"].value_counts()
        rec["n_critical"] = int(vc.get("CRITICAL", 0))
        rec["n_high"] = int(vc.get("HIGH", 0))
        rec["n_medium"] = int(vc.get("MEDIUM", 0))
        rec["n_data_gap"] = int(vc.get("DATA_GAP", 0))
    if cluster_result is not None and getattr(cluster_result, "k", 0):
        rec["kmeans_k"] = int(cluster_result.k)
        rec["silhouette"] = round(
            cluster_result.metrics.get(cluster_result.k, {}).get("silhouette", float("nan")), 4)
    if validation_findings is not None and not validation_findings.empty and features is not None:
        denom = max(len(features), 1)
        rec["validation_error_rate"] = round(len(validation_findings) / denom, 4)
    rec["feedback_fp_rate"] = round(feedback_fp_rate, 4) if feedback_fp_rate is not None else None
    rec["runtime_sec"] = round(runtime_sec, 3) if runtime_sec is not None else None
    rec["data_version"] = data_version or "n/a"
    rec.update(_versions())
    return rec


def log_run(record: dict) -> pd.DataFrame:
    """Append a run record to the performance log and return the full log."""
    row = pd.DataFrame([{c: record.get(c) for c in PERF_COLUMNS}])
    if PERF_LOG.exists():
        try:
            prev = pd.read_csv(PERF_LOG)
            out = pd.concat([prev, row], ignore_index=True)
        except Exception:  # noqa: BLE001
            out = row
    else:
        out = row
    out.to_csv(PERF_LOG, index=False, encoding="utf-8-sig")
    LOG.info("Logged run -> %s (total %d runs)", PERF_LOG.name, len(out))
    return out


def load_performance_log() -> pd.DataFrame:
    if PERF_LOG.exists():
        try:
            return pd.read_csv(PERF_LOG)
        except Exception:  # noqa: BLE001
            return pd.DataFrame(columns=PERF_COLUMNS)
    return pd.DataFrame(columns=PERF_COLUMNS)


def cluster_stability(prev_assign: pd.DataFrame | None, cur_assign: pd.DataFrame) -> float | None:
    """Share of banks keeping the same cluster id between two runs (rough stability)."""
    if prev_assign is None or prev_assign.empty or cur_assign is None or cur_assign.empty:
        return None
    a = prev_assign.set_index("bank_id")["cluster_id"]
    b = cur_assign.set_index("bank_id")["cluster_id"]
    common = a.index.intersection(b.index)
    if len(common) == 0:
        return None
    return round(float((a.loc[common].values == b.loc[common].values).mean()), 4)
