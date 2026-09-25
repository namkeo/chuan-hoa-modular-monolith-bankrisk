"""Serialize the analysis pipeline output to JSON for the Node/React web UI.

The Node backend spawns ``python -m src.api_export <frequency>`` which runs the full
pipeline and writes ``outputs/api/<frequency>.json`` plus ``outputs/api/meta.json``.
React then consumes these via the Express REST API — no Python<->JS runtime bridge.

Everything here is plain JSON-safe (no NaN/Timestamp); helpers below sanitize values.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .data_loader import missing_metric_table, scan_pdf_files
from .feedback import false_positive_stats, load_feedback, suggest_adjustments
from .pdf_rule_extractor import extract_rules_from_pdfs
from .performance_tracker import load_performance_log
from .pipeline import available_frequencies, run_pipeline
from .reporting import DISCLAIMER, generate_all_reports
from .utils import DATA_ROOT, LOG, OUTPUTS_DIR, PROJECT_ROOT, load_config

API_DIR = OUTPUTS_DIR / "api"
API_DIR.mkdir(parents=True, exist_ok=True)

ID_COLS = {"bank_id", "bank_name", "period", "period_ts"}


# --------------------------------------------------------------------------- #
# JSON sanitation
# --------------------------------------------------------------------------- #
def _clean(value):
    """Convert a single value into a JSON-safe Python primitive."""
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if (np.isnan(f) or np.isinf(f)) else round(f, 4)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (np.ndarray, list, tuple)):
        return [_clean(v) for v in value]
    return value


def _records(df: pd.DataFrame, cols: list[str] | None = None,
             limit: int | None = None, name: str = "payload"):
    """DataFrame -> list of JSON-safe dicts (selected/limited).

    Cắt bớt dòng luôn được ghi log: một cap âm thầm từng xóa sạch các kỳ cũ khỏi
    giao diện, khiến kỳ đó trông như "không có vi phạm" trong khi thực tế có.
    """
    if df is None or df.empty:
        return []
    out = df
    if cols:
        out = out[[c for c in cols if c in out.columns]]
    if limit and len(out) > limit:
        LOG.warning("%s: cắt %d/%d dòng khi xuất API (limit=%d) — phần bị bỏ sẽ "
                    "KHÔNG hiển thị trên giao diện", name, len(out) - limit,
                    len(out), limit)
        out = out.head(limit)
    recs = out.to_dict(orient="records")
    return [{k: _clean(v) for k, v in r.items()} for r in recs]


# --------------------------------------------------------------------------- #
# Build the per-frequency payload
# --------------------------------------------------------------------------- #
def build_payload(frequency: str, use_cache: bool = True) -> dict:
    res = run_pipeline(DATA_ROOT, frequency, use_cache=use_cache, save_models=False)
    if res.features.empty:
        return {"frequency": frequency, "empty": True,
                "generated_at": datetime.now().isoformat(timespec="seconds")}

    feats = res.features
    val_cols = [c for c in feats.columns if c not in ID_COLS]
    missing_pct = round(float(feats[val_cols].isna().mean().mean()) * 100, 2) if val_cols else 0.0

    scores = res.risk_scores
    ranking = res.bank_ranking
    rf = res.rule_findings

    # Rule findings are exported in full: the UI filters them by the selected
    # as-of period, so dropping rows removes whole periods from every page that
    # reads them. (A previous 8000-row cap silently deleted 2023-01..2024-06 —
    # 2631 real violations, 975 of them CRITICAL — leaving those periods blank.)
    # Ordering is display-only: most-recent period first, severest first.
    rf_export = rf
    if not rf.empty:
        _sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "DATA_GAP": 4}
        rf_export = (rf.assign(_sev=rf["severity"].map(_sev_rank).fillna(9))
                     .sort_values(["period", "_sev"], ascending=[False, True])
                     .drop(columns="_sev"))

    # KPI summary.
    level_counts = (ranking["risk_level"].value_counts().to_dict()
                    if not ranking.empty else {})
    sev_counts = rf["severity"].value_counts().to_dict() if not rf.empty else {}

    summary = {
        "n_banks": int(feats["bank_id"].nunique()),
        "n_periods": int(feats["period"].nunique()),
        "n_files": len(res.load.files),
        "missing_pct": missing_pct,
        "anomaly_rate": (round(float(res.anomalies["anomaly_label"].mean()) * 100, 2)
                         if not res.anomalies.empty else 0.0),
        "n_anomalies": (int(res.anomalies["anomaly_label"].sum())
                        if not res.anomalies.empty else 0),
        "cluster_k": res.cluster_k,
        "silhouette": _clean(res.cluster_metrics.get(res.cluster_k, {}).get("silhouette")),
        "runtime_sec": res.runtime_sec,
        "level_counts": {k: int(v) for k, v in level_counts.items()},
        "severity_counts": {k: int(v) for k, v in sev_counts.items()},
        "n_high_risk_periods": (int(res.high_risk_periods["is_high_risk"].sum())
                                if not res.high_risk_periods.empty else 0),
    }

    # Heatmap (bank x period final_risk_score).
    heatmap = {"banks": [], "periods": [], "z": []}
    if not scores.empty:
        pivot = scores.pivot_table(index="bank_id", columns="period",
                                   values="final_risk_score", aggfunc="last")
        pivot = pivot.reindex(sorted(pivot.columns), axis=1)
        heatmap = {
            "banks": list(pivot.index),
            "periods": [str(c) for c in pivot.columns],
            "z": [[_clean(v) for v in row] for row in pivot.values],
        }

    # Domain means (latest snapshot).
    domain_means = {}
    for col, key in [("credit_risk_score", "credit"), ("liquidity_risk_score", "liquidity"),
                     ("fraud_risk_proxy_score", "fraud"), ("failure_risk_proxy_score", "failure")]:
        if not ranking.empty and col in ranking.columns:
            domain_means[key] = _clean(ranking[col].mean())

    payload = {
        "frequency": frequency,
        "empty": False,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "disclaimer": DISCLAIMER,
        "summary": summary,
        "files": _records(pd.DataFrame(res.load.files)),
        "unmapped_labels": [{"label": k, "count": int(v)}
                            for k, v in list(res.load.unmapped_labels.items())[:40]],
        "missing_by_metric": _records(missing_metric_table(feats, res.load.panel)),
        "ranking": _records(ranking, [
            "bank_id", "bank_name", "period", "final_risk_score", "risk_level",
            "rule_violation_score", "anomaly_score_norm", "trend_risk_score",
            "cluster_risk_score", "cluster_risk_label", "credit_risk_score",
            "liquidity_risk_score", "fraud_risk_proxy_score",
            "failure_risk_proxy_score", "worst_rule_severity",
            "credit_structure_score", "credit_provision_score",
            "credit_concentration_score", "credit_offbalance_score",
            "credit_capital_score", "liq_deposit_score", "liq_wholesale_score",
            "liq_secondary_score", "liq_market_score", "credit_flag_clusters",
            "liq_flag_clusters", "fraud_flag_clusters", "fraud_flags"]),
        "periods": _periods_payload(feats),
        "scores": _records(scores, [
            "bank_id", "bank_name", "period", "final_risk_score", "risk_level",
            "rule_violation_score", "anomaly_score_norm", "trend_risk_score",
            "cluster_risk_score", "cluster_risk_label", "credit_risk_score",
            "liquidity_risk_score", "fraud_risk_proxy_score",
            "failure_risk_proxy_score", "worst_rule_severity",
            "credit_structure_score", "credit_provision_score",
            "credit_concentration_score", "credit_offbalance_score",
            "credit_capital_score", "liq_deposit_score", "liq_wholesale_score",
            "liq_secondary_score", "liq_market_score", "credit_flag_clusters",
            "liq_flag_clusters", "fraud_flag_clusters", "fraud_flags"],
            limit=8000, name="scores"),
        "heatmap": heatmap,
        "domain_means": domain_means,
        "rule_findings": _records(rf_export, [
            "bank_id", "period", "rule_id", "rule_name", "metric", "metric_value",
            "operator", "threshold", "severity", "finding_type", "risk_domain",
            "legal_source", "article_reference", "description",
            "audit_recommendation"],
            name="rule_findings"),
        "rules_config": _rules_config(),
        "anomalies": _records(
            res.anomalies.sort_values("anomaly_score", ascending=False)
            if not res.anomalies.empty else res.anomalies,
            ["bank_id", "period", "anomaly_score", "anomaly_label", "top_features"],
            limit=8000, name="anomalies"),
        "anomaly_features": res.anomaly_features,
        "clusters": {
            "k": res.cluster_k,
            "metrics": {str(k): {kk: _clean(vv) for kk, vv in v.items()}
                        for k, v in res.cluster_metrics.items()},
            "profiles": _records(res.cluster_profiles),
            "projection": _records(res.cluster_projection),
            "assignment": _records(
                res.cluster_table[["bank_id", "cluster_id", "cluster_risk_label",
                                   "cluster_risk_score"]].drop_duplicates("bank_id")
                if not res.cluster_table.empty else res.cluster_table),
        },
        "systemic_stress": _records(res.systemic_stress, [
            "period", "systemic_stress_index", "systemic_stress_pct"]),
        "high_risk_periods": _records(res.high_risk_periods, [
            "period", "period_risk_score", "is_high_risk", "n_critical_banks",
            "n_high_banks", "anomaly_rate", "systemic_stress_pct", "worsen_share",
            "risk_domains", "reason", "recommended_audit_focus"]),
        "validation": _records(res.validation, [
            "category", "severity", "bank_id", "period", "metric", "message"],
            name="validation"),
        "validation_counts": (res.validation["category"].value_counts().to_dict()
                              if not res.validation.empty else {}),
        "series": _series_payload(feats, res.base_metrics),
        "base_metrics": res.base_metrics,
        "banks": sorted(feats["bank_id"].unique().tolist()),
        "ews": _ews_payload(res),
        "stress": _stress_payload(res),
        "combined": _combined_payload(res),
    }
    return payload


def _combined_payload(res) -> dict:
    """Cross-frequency provenance for the 'combined' view (empty for single-freq)."""
    sm = getattr(res, "combined_source_map", {}) or {}
    if not sm:
        return {"is_combined": False}
    rows = [{"metric": m, "primary_frequency": v.get("primary"),
             "sources": ", ".join(v.get("sources", [])),
             "is_cross_frequency": len(v.get("sources", [])) > 1}
            for m, v in sorted(sm.items())]
    by_src: dict = {}
    for r in rows:
        by_src[r["primary_frequency"]] = by_src.get(r["primary_frequency"], 0) + 1
    return {
        "is_combined": True,
        "meta": getattr(res, "combined_meta", {}),
        "by_source": by_src,
        "source_map": rows,
    }


def _stress_payload(res) -> dict:
    """Stress-test payload: scenarios, per-bank results, system summary, reverse stress."""
    return {
        "snapshot_period": res.stress_snapshot,
        "scenarios": [{
            "id": s.get("id"), "name": s.get("name"), "description": s.get("description"),
            "npl_shock_pp": s.get("npl_shock_pp"), "rwa_shock": s.get("rwa_shock"),
            "lgd": s.get("lgd"), "deposit_runoff": s.get("deposit_runoff"),
            "wholesale_runoff": s.get("wholesale_runoff"), "hqla_haircut": s.get("hqla_haircut"),
        } for s in (res.stress_scenarios or [])],
        "system": _records(res.stress_system),
        "results": _records(res.stress_results, [
            "bank_id", "bank_name", "period", "scenario_id", "scenario_name", "baseline_car",
            "stressed_car", "car_delta", "credit_loss", "capital_shortfall",
            "passes_capital", "capital_status", "liq_method", "stressed_lcr",
            "stressed_ldr", "baseline_ldr", "liquidity_gap", "deposit_outflow",
            "passes_liquidity", "liquidity_status", "total_assets", "data_gaps"]),
        "breaking_points": _records(res.stress_breaking),
    }


def _ews_payload(res) -> dict:
    """Early Warning System payload: latest per-bank, system timeline, watchlist."""
    latest = res.ews_latest
    sys_df = res.ews_system
    level_counts = (latest["ews_level"].value_counts().to_dict()
                    if latest is not None and not latest.empty else {})
    sys_now = {}
    if sys_df is not None and not sys_df.empty:
        last = sys_df.iloc[-1]
        sys_now = {k: _clean(last[k]) for k in
                   ["period", "system_level", "system_label", "mean_ews",
                    "share_warning_plus", "n_alarm", "n_warning", "mean_ews_mom"]
                   if k in sys_df.columns}
    return {
        "metrics_used": res.ews_metrics,
        "level_counts": {k: int(v) for k, v in level_counts.items()},
        "system_now": sys_now,
        "latest": _records(latest, [
            "bank_id", "bank_name", "period", "ews_score", "ews_level", "ews_label",
            "score_delta", "escalating", "sig_proximity", "sig_trend",
            "sig_acceleration", "sig_volatility", "sig_breach_streak",
            "sig_anomaly_persistence", "projected_periods_to_breach",
            "projected_breach_metric", "n_in_buffer", "n_breached", "n_data_gap",
            "risk_domains", "drivers"]),
        "system": _records(sys_df, [
            "period", "mean_ews", "share_warning_plus", "n_warning_plus", "n_alarm",
            "n_warning", "system_level", "system_label", "mean_ews_mom"]),
        "emerging": _records(res.ews_emerging),
        "trajectory": _ews_trajectory(res.ews_table),
        "table": _records(res.ews_table, [
            "bank_id", "period", "ews_score", "ews_level", "ews_label",
            "sig_proximity", "sig_trend", "sig_acceleration", "sig_volatility",
            "sig_breach_streak", "sig_anomaly_persistence", "n_breached",
            "projected_periods_to_breach", "projected_breach_metric",
            "risk_domains", "drivers"], limit=12000, name="ews_table"),
    }


def _ews_trajectory(table: pd.DataFrame) -> dict:
    """Per-bank EWS score over time for the trajectory chart (compact)."""
    out: dict = {"periods": [], "data": {}}
    if table is None or table.empty:
        return out
    t = table.sort_values("period_ts")
    out["periods"] = [str(p) for p in t["period"].drop_duplicates()]
    for bid, sub in t.groupby("bank_id"):
        m = dict(zip(sub["period"].astype(str), sub["ews_score"]))
        out["data"][bid] = [_clean(m.get(p)) for p in out["periods"]]
    return out


def _series_payload(feats: pd.DataFrame, base_metrics: list[str]) -> dict:
    """Per bank, per key-metric time series for the Time Series page (compact)."""
    key_metrics = [m for m in ["npl_ratio", "ldr", "car_solo", "roa",
                               "liquidity_reserve_ratio", "group2_ratio",
                               "st_funding_for_mlt_loans", "credit_growth_yoy",
                               # Chỉ tiêu bổ sung (readme_explain_bo_sung.docx §13.5)
                               "provision_to_loans", "credit_cost_ratio",
                               "accrued_interest_to_loans", "offbalance_to_assets",
                               "unsecured_loan_ratio", "risky_sector_ratio",
                               "large_borrower_ratio", "mlt_loan_ratio",
                               "wholesale_funding_share", "liquid_assets_to_deposits",
                               "casa", "solvency_30d_vnd", "solvency_30d_fx"]
                   if m in feats.columns]
    out: dict = {"metrics": key_metrics, "data": {}}
    df = feats.sort_values("period_ts")
    for bid, sub in df.groupby("bank_id"):
        out["data"][bid] = {
            "periods": [str(p) for p in sub["period"]],
            **{m: [_clean(v) for v in sub[m]] for m in key_metrics},
        }
    return out


def _periods_payload(feats: pd.DataFrame) -> dict:
    """Available periods (sorted) decomposed into year + sub-period for the time picker."""
    import re
    pers = (feats[["period", "period_ts"]].drop_duplicates()
            .sort_values("period_ts"))
    items = []
    for _, r in pers.iterrows():
        p = str(r["period"])
        year = sub = sub_label = None
        kind = "year"
        if re.match(r"^\d{4}-\d{2}-\d{2}$", p):           # daily
            kind = "day"; year = int(p[:4]); sub = p; sub_label = p
        elif re.match(r"^\d{4}-\d{2}$", p):                # monthly
            kind = "month"; year = int(p[:4]); sub = int(p[5:7]); sub_label = f"Tháng {sub}"
        elif re.match(r"^\d{4}Q[1-4]$", p):                # quarterly
            kind = "quarter"; year = int(p[:4]); sub = int(p[-1]); sub_label = f"Quý {sub}"
        elif re.match(r"^\d{4}$", p):                      # yearly
            kind = "year"; year = int(p); sub = None; sub_label = p
        items.append({"period": p, "year": year, "sub": sub,
                      "sub_label": sub_label, "kind": kind})
    years = sorted({i["year"] for i in items if i["year"] is not None})
    latest = items[-1]["period"] if items else None
    return {"kind": items[0]["kind"] if items else "period", "items": items,
            "years": years, "latest": latest}


def _rules_config() -> list[dict]:
    rules = load_config("regulatory_rules").get("rules", [])
    return [{
        "rule_id": r.get("rule_id"), "rule_name": r.get("rule_name"),
        "metric": r.get("metric"), "operator": r.get("operator"),
        "threshold": _clean(r.get("threshold")), "severity": r.get("severity"),
        "status": r.get("status"), "risk_domain": r.get("risk_domain"),
        "legal_source": r.get("legal_source"),
        "article_reference": r.get("article_reference"), "formula": r.get("formula"),
    } for r in rules]


# --------------------------------------------------------------------------- #
# Side payloads (not frequency-specific)
# --------------------------------------------------------------------------- #
def build_meta() -> dict:
    from .hyperopt import current_tuned
    freqs = available_frequencies(DATA_ROOT)
    tuned = current_tuned()
    return {
        "frequencies": freqs,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(PROJECT_ROOT),
        "data_root": str(DATA_ROOT),
        "disclaimer": DISCLAIMER,
        "versions": load_config("model_config").get("versions", {}),
        "tuned": {"applied": bool(tuned.get("applied")), "tuned_at": tuned.get("tuned_at"),
                  "isolation_forest": tuned.get("isolation_forest"),
                  "kmeans": tuned.get("kmeans")},
    }


def _features_for(frequency: str):
    """Cheaply build the feature table for a frequency (for tuning, no full pipeline)."""
    from .data_loader import load_all
    from .feature_engineering import build_features
    load = load_all(DATA_ROOT, use_cache=True)
    if frequency not in load.wide:
        return None, []
    feats = build_features(load.wide[frequency], frequency)
    return feats, feats.attrs.get("base_metrics", [])


def run_tuning(frequency: str, model: str, criterion: str = "auto") -> dict:
    """Run hyperparameter tuning for a model and return a JSON-safe payload."""
    from .hyperopt import tune_isolation_forest, tune_kmeans
    feats, bm = _features_for(frequency)
    if feats is None or feats.empty:
        return {"ok": False, "error": f"Không có dữ liệu cho '{frequency}'"}
    if model == "kmeans":
        tr = tune_kmeans(feats, bm, criterion=(criterion if criterion != "auto" else "silhouette"))
    else:
        tr = tune_isolation_forest(feats, bm, criterion=criterion)
    return {
        "ok": True, "model": tr.model, "criterion": tr.criterion, "note": tr.note,
        "n_samples": tr.n_samples, "best": tr.best, "current": tr.current,
        "leaderboard": _records(tr.leaderboard, limit=200, name="leaderboard"),
    }


def build_performance() -> dict:
    log = load_performance_log()
    fp = false_positive_stats()
    return {
        "log": _records(log),
        "feedback_stats": {k: _clean(v) if not isinstance(v, dict) else
                           {kk: _clean(vv) for kk, vv in v.items()}
                           for k, v in fp.items()},
        "suggestions": suggest_adjustments(),
        "feedback": _records(load_feedback(), limit=500, name="feedback"),
    }


def build_pdf_status() -> dict:
    pdfs = scan_pdf_files(DATA_ROOT)
    res = extract_rules_from_pdfs(pdfs, use_ocr=False, write_csv=True)
    return {
        "file_status": _records(res.file_status, [
            "pdf_file", "n_pages", "pages_with_text", "total_chars", "status",
            "n_candidates"]),
        "candidates": _records(res.candidates, limit=300, name="pdf_candidates"),
        "csv_path": res.csv_path,
    }


import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27017/")
DB_NAME = "bank_risk_db"


def save_to_mongo(collection_name: str, query: dict, data: dict) -> None:
    """Save/Upsert payload document into MongoDB."""
    try:
        import pymongo
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[DB_NAME]
        db[collection_name].replace_one(query, data, upsert=True)
        LOG.info("Saved payload to MongoDB -> %s (query=%s)", collection_name, query)
    except Exception as exc:  # noqa: BLE001
        LOG.warning("MongoDB save skipped / failed: %s", exc)


# Chèn theo lô thay vì cắt bớt. Một `insert_many` duy nhất bị chặn bởi giới hạn
# kích thước thông điệp của MongoDB, và trước đây chỗ này né bằng cách cắt còn
# 5.000 dòng — với tần suất `combined`, 9.747 trong 14.747 phát hiện không bao giờ
# tới được giao diện, trong đó 489 vi phạm CRITICAL thuộc 23 kỳ báo cáo, khiến các
# kỳ đó trông như không có vi phạm. Quyết định "giữ lại bao nhiêu" không thuộc về
# tầng ghi dữ liệu: đã phát hiện thì phải lưu đủ.
INSERT_BATCH_SIZE = 1000


def _insert_all(collection, docs: list[dict], name: str) -> int:
    """Chèn toàn bộ `docs` theo lô. Trả về số bản ghi đã ghi."""
    written = 0
    for start in range(0, len(docs), INSERT_BATCH_SIZE):
        batch = docs[start:start + INSERT_BATCH_SIZE]
        collection.insert_many(batch)
        written += len(batch)
    if written != len(docs):  # không bao giờ xảy ra, nhưng im lặng thì nguy hiểm
        LOG.error("%s: chỉ ghi được %d/%d bản ghi", name, written, len(docs))
    else:
        LOG.info("%s: đã ghi đủ %d bản ghi", name, written)
    return written


# --------------------------------------------------------------------------- #
# Writers / CLI
# --------------------------------------------------------------------------- #
def export_frequency(frequency: str, use_cache: bool = True,
                     payload: dict | None = None) -> Path:
    """Ghi payload của một tần suất ra tệp JSON và MongoDB.

    ``payload`` cho phép người gọi truyền lại kết quả đã dựng sẵn. db_seed từng gọi
    ``export_frequency()`` rồi ``build_payload()`` liền sau, tức chạy trọn pipeline
    HAI LẦN cho mỗi tần suất (riêng 'combined' là ~100 giây mỗi lượt).
    """
    if payload is None:
        payload = build_payload(frequency, use_cache=use_cache)
    path = API_DIR / f"{frequency}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    LOG.info("Wrote API payload -> %s (%.1f KB)", path, path.stat().st_size / 1024)

    try:
        import pymongo
        uris = []
        if os.getenv("MONGO_URI"):
            uris.append(os.getenv("MONGO_URI"))
        uris.extend(["mongodb://admin:12345678@localhost:27018/", "mongodb://admin:12345678@localhost:27017/"])
        client = None
        for uri in uris:
            try:
                c = pymongo.MongoClient(uri, serverSelectionTimeoutMS=1500)
                c.admin.command("ping")
                client = c
                break
            except Exception:
                continue

        if client is not None and not payload.get("empty"):
            db = client[DB_NAME]

            # 1. Save lean metadata document into api_payloads (~2MB, contains series, scores, validation, summary, periods)
            lean_payload = {k: v for k, v in payload.items() if k not in ("rule_findings", "anomalies")}
            lean_payload["frequency"] = frequency
            lean_payload["empty"] = False
            db["api_payloads"].replace_one({"frequency": frequency}, lean_payload, upsert=True)

            # 2. Save rule findings collection
            rf_list = payload.get("rule_findings", [])
            if rf_list:
                db["computed_rule_findings"].delete_many({"frequency": frequency})
                for r in rf_list:
                    r["frequency"] = frequency
                _insert_all(db["computed_rule_findings"], rf_list, "computed_rule_findings")

            # 3. Save anomalies collection
            anom_list = payload.get("anomalies", [])
            if anom_list:
                db["computed_anomalies"].delete_many({"frequency": frequency})
                for a in anom_list:
                    a["frequency"] = frequency
                _insert_all(db["computed_anomalies"], anom_list, "computed_anomalies")

            # 4. Save clusters, EWS, Stress
            if "clusters" in payload:
                db["computed_clusters"].replace_one({"frequency": frequency}, {"frequency": frequency, "data": payload["clusters"]}, upsert=True)
            if "ews" in payload:
                db["computed_ews_indicators"].replace_one({"frequency": frequency}, {"frequency": frequency, "data": payload["ews"]}, upsert=True)
            if "stress" in payload:
                db["computed_stress_test_results"].replace_one({"frequency": frequency}, {"frequency": frequency, "data": payload["stress"]}, upsert=True)

            LOG.info("Saved structured payload for '%s' to MongoDB", frequency)
    except Exception as exc:
        LOG.warning("MongoDB structured save skipped / failed: %s", exc)

    return path


def export_meta() -> Path:
    meta = build_meta()
    path = API_DIR / "meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    save_to_mongo("api_meta", {"type": "meta"}, meta)
    return path


def export_side() -> None:
    perf = build_performance()
    (API_DIR / "performance.json").write_text(
        json.dumps(perf, ensure_ascii=False), encoding="utf-8")
    save_to_mongo("api_performance", {"type": "performance"}, perf)

    pdf_stat = build_pdf_status()
    (API_DIR / "pdf_status.json").write_text(
        json.dumps(pdf_stat, ensure_ascii=False), encoding="utf-8")
    save_to_mongo("api_pdf_status", {"type": "pdf_status"}, pdf_stat)



def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "all"
    try:
        if cmd == "meta":
            export_meta()
        elif cmd == "performance":
            export_side()
        elif cmd == "report":
            freq = argv[1] if len(argv) > 1 else "quarterly"
            res = run_pipeline(DATA_ROOT, freq, use_cache=True)
            paths = generate_all_reports(res)
            print(json.dumps(paths, ensure_ascii=False))
            return 0
        elif cmd == "tune":
            freq = argv[1] if len(argv) > 1 else "monthly"
            model = argv[2] if len(argv) > 2 else "isolation_forest"
            crit = argv[3] if len(argv) > 3 else "auto"
            print(json.dumps(run_tuning(freq, model, crit), ensure_ascii=False))
            return 0
        elif cmd == "tune-apply":
            from .hyperopt import apply_tuned
            payload = json.loads(argv[argv.index("--json") + 1]) if "--json" in argv else {}
            apply_tuned(isolation_forest=payload.get("isolation_forest"),
                        kmeans=payload.get("kmeans"))
            export_meta()
            print(json.dumps({"ok": True, "applied": True}, ensure_ascii=False))
            return 0
        elif cmd == "tune-reset":
            from .hyperopt import reset_tuned
            reset_tuned()
            export_meta()
            print(json.dumps({"ok": True, "applied": False}, ensure_ascii=False))
            return 0
        elif cmd == "all":
            export_meta()
            export_side()
            for f in available_frequencies(DATA_ROOT):
                export_frequency(f)
        else:  # treat cmd as a frequency
            export_meta()
            export_frequency(cmd, use_cache=("--no-cache" not in argv))
        print(json.dumps({"ok": True, "cmd": cmd}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        LOG.exception("api_export failed")
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
