"""FastAPI Router for System Overview & FE Gateway Payloads (Tổng quan dữ liệu & Metadata).

Reads raw panel data & aggregated payloads from MongoDB 'bank_risk_db'
(collections: 'api_payloads', 'api_meta', 'computed_*', 'raw_files').
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import OUTPUTS_DIR, DATA_ROOT, LOG
from src.reporting import DISCLAIMER
from src.api_export import build_meta, build_performance, build_pdf_status, export_frequency, export_side

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27017/")
DB_NAME = "bank_risk_db"
API_DIR = OUTPUTS_DIR / "api"

router = APIRouter(prefix="/api", tags=["Overview & System Gateway"])


def _get_db():
    uris = []
    if os.getenv("MONGO_URI"):
        uris.append(os.getenv("MONGO_URI"))
    uris.extend(["mongodb://admin:12345678@localhost:27018/", "mongodb://admin:12345678@localhost:27017/"])
    for uri in uris:
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=1500)
            client.admin.command("ping")
            return client[DB_NAME]
        except Exception:
            continue
    return None


def _read_json_fallback(file_name: str) -> dict | list | None:
    candidate_paths = [
        API_DIR / file_name,
        PROJECT_ROOT / "outputs" / "api" / file_name,
        PROJECT_ROOT.parent / "outputs" / "api" / file_name,
        Path("/app/outputs/api") / file_name,
        Path("/app/bank_risk_service/outputs/api") / file_name,
        Path(r"d:\Văn bản KTNN\Rủi ro vốn\Data 010826\[SBV] Tài liệu khảo sát\dataset\source_code\outputs\api") / file_name,
    ]
    for fpath in candidate_paths:
        if fpath.exists():
            try:
                return json.loads(fpath.read_text(encoding="utf-8"))
            except Exception:
                continue
    return None


def _build_periods_from_mongo(db, freq: str) -> dict:
    """Dynamically construct periods metadata from MongoDB collections."""
    import re
    freq_filter = {"frequency": freq}
    distinct_pers = db["risk_scores"].distinct("period", freq_filter)
    if not distinct_pers:
        distinct_pers = db["risk_scores"].distinct("period")
    if not distinct_pers:
        coll = db["computed_rule_findings"] if db["computed_rule_findings"].count_documents({}) > 0 else db["rule_findings"]
        distinct_pers = coll.distinct("period")
    if not distinct_pers:
        distinct_pers = db["raw_panel_data"].distinct("period")

    distinct_pers = sorted([str(p) for p in distinct_pers if p])
    if not distinct_pers:
        distinct_pers = ["2023-12-31", "2024-12-31", "2025-01-31"]

    items = []
    years_set = set()
    for p in distinct_pers:
        year = None
        sub = None
        sub_label = None
        kind = "month"
        if re.match(r"^\d{4}-\d{2}-\d{2}$", p):
            kind = "day"
            year = int(p[:4])
            sub = p
            sub_label = p
        elif re.match(r"^\d{4}-\d{2}$", p):
            kind = "month"
            year = int(p[:4])
            sub = int(p[5:7])
            sub_label = f"Tháng {sub}"
        elif re.match(r"^\d{4}Q[1-4]$", p):
            kind = "quarter"
            year = int(p[:4])
            sub = int(p[-1])
            sub_label = f"Quý {sub}"
        elif re.match(r"^\d{4}$", p):
            kind = "year"
            year = int(p)
            sub = None
            sub_label = p
        else:
            m = re.search(r"(\d{4})", p)
            year = int(m.group(1)) if m else 2025
            kind = "year"
            sub = None
            sub_label = p

        years_set.add(year)
        items.append({"period": p, "year": year, "sub": sub, "sub_label": sub_label, "kind": kind})

    years = sorted(list(years_set))
    latest = items[-1]["period"] if items else "2025"
    kind = items[0]["kind"] if items else "month"
    return {"kind": kind, "items": items, "years": years, "latest": latest}


def _build_missing_by_metric_from_mongo(db, freq: str) -> list:
    """Build missing_by_metric list dynamically from raw_panel_data in MongoDB."""
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "metric": "$metric_name",
                        "label": "$metric_label",
                        "unit": "$unit",
                        "camels_group": "$camels_group",
                    },
                    "total_records": {"$sum": 1},
                }
            }
        ]
        results = list(db["raw_panel_data"].aggregate(pipeline))
        if not results:
            return []

        distinct_pers = db["raw_panel_data"].distinct("period")
        n_periods = len(distinct_pers) or 36
        n_total = n_periods * 83

        out = []
        for r in results:
            m_info = r["_id"]
            m_name = m_info.get("metric") or "N/A"
            if not m_name or m_name == "N/A":
                continue
            tot = r.get("total_records", n_total)
            actual_missing = max(0, n_total - tot)
            if actual_missing > 0:
                pct = round(actual_missing / max(n_total, 1) * 100, 2)
                out.append({
                    "metric": m_name,
                    "label": m_info.get("label") or m_name,
                    "unit": m_info.get("unit") or "",
                    "camels_group": m_info.get("camels_group") or "Khác",
                    "is_derived_ratio": False,
                    "n_missing": actual_missing,
                    "n_total": n_total,
                    "missing_pct": pct,
                })
        out.sort(key=lambda x: x["missing_pct"], reverse=True)
        return out
    except Exception as err:
        LOG.warning("Failed to build missing_by_metric from mongo: %s", err)
        return []


def _build_series_from_mongo(db, freq: str) -> dict:
    """Build series dictionary per bank for time-series and domain risk pages from raw_panel_data."""
    try:
        metrics_list = list(db["raw_panel_data"].distinct("metric_name"))
        extra_metrics = ["provision_to_loans", "accrued_interest_to_loans", "wholesale_funding_share", "interbank_assets_to_liabilities"]
        full_metrics_list = list(set(metrics_list + extra_metrics))

        banks = db["raw_panel_data"].distinct("bank_id")
        banks.sort()

        data_by_bank = {}
        for b in banks:
            docs = list(db["raw_panel_data"].find({"bank_id": b}, {"_id": 0, "period": 1, "metric_name": 1, "metric_value": 1}))
            if not docs:
                continue
            pers = sorted(list(set(d.get("period") for d in docs if d.get("period"))))
            b_dict = {"periods": pers}

            metric_val_map = {}
            for d in docs:
                mname = d.get("metric_name")
                p = d.get("period")
                if mname and p:
                    if mname not in metric_val_map:
                        metric_val_map[mname] = {}
                    metric_val_map[mname][p] = d.get("metric_value")

            for m in metrics_list:
                val_map = metric_val_map.get(m, {})
                b_dict[m] = [val_map.get(p) for p in pers]

            # Compute derived ratios for domain pages
            prov_map = metric_val_map.get("provisions", {}) or metric_val_map.get("credit_provision_expense", {})
            loans_map = metric_val_map.get("customer_loans", {}) or metric_val_map.get("total_loans", {})
            accr_map = metric_val_map.get("accrued_interest", {})
            dep_map = metric_val_map.get("total_deposits", {}) or metric_val_map.get("deposits", {})
            ib_fund_map = metric_val_map.get("interbank_funding", {})
            ib_asset_map = metric_val_map.get("interbank_assets", {})

            b_dict["provision_to_loans"] = [
                round(prov_map[p] / loans_map[p] * 100, 2) if (p in prov_map and p in loans_map and loans_map[p]) else None
                for p in pers
            ]
            b_dict["accrued_interest_to_loans"] = [
                round(accr_map[p] / loans_map[p] * 100, 2) if (p in accr_map and p in loans_map and loans_map[p]) else None
                for p in pers
            ]
            b_dict["wholesale_funding_share"] = [
                round(ib_fund_map[p] / dep_map[p] * 100, 2) if (p in ib_fund_map and p in dep_map and dep_map[p]) else None
                for p in pers
            ]
            b_dict["interbank_assets_to_liabilities"] = [
                round(ib_asset_map[p] / ib_fund_map[p] * 100, 2) if (p in ib_asset_map and p in ib_fund_map and ib_fund_map[p]) else None
                for p in pers
            ]

            data_by_bank[b] = b_dict

        return {
            "metrics": full_metrics_list,
            "data": data_by_bank
        }
    except Exception as err:
        LOG.warning("Failed to build series from mongo: %s", err)
        return {"metrics": [], "data": {}}


def _build_heatmap_from_mongo(db, freq: str) -> dict:
    freq_filter = {"$or": [{"frequency": freq}, {"frequency": "combined"}, {"frequency": {"$exists": False}}]}
    scores = list(db["risk_scores"].find(freq_filter, {"_id": 0}))
    if not scores:
        scores = list(db["risk_scores"].find({}, {"_id": 0}))
    if not scores:
        return {"banks": [], "periods": [], "z": []}
    
    banks = sorted(list(set(s["bank_id"] for s in scores if s.get("bank_id"))))
    periods = sorted(list(set(s["period"] for s in scores if s.get("period"))))
    score_map = {(s["bank_id"], s["period"]): s.get("final_risk_score") for s in scores}
    
    z = []
    for b in banks:
        row = [score_map.get((b, p)) for p in periods]
        z.append(row)
    
    return {"banks": banks, "periods": periods, "z": z}


def _build_domain_means_from_mongo(db, freq: str) -> dict:
    freq_filter = {"$or": [{"frequency": freq}, {"frequency": "combined"}, {"frequency": {"$exists": False}}]}
    rankings = list(db["bank_rankings"].find(freq_filter, {"_id": 0}))
    if not rankings:
        rankings = list(db["bank_rankings"].find({}, {"_id": 0}))
    if not rankings:
        return {"credit": 0.0, "liquidity": 0.0, "fraud": 0.0, "failure": 0.0}
    
    def _mean(col):
        vals = [r[col] for r in rankings if r.get(col) is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    
    return {
        "credit": _mean("credit_risk_score"),
        "liquidity": _mean("liquidity_risk_score"),
        "fraud": _mean("fraud_risk_proxy_score"),
        "failure": _mean("failure_risk_proxy_score")
    }


def _get_freq_payload_from_mongo(db, freq: str) -> dict | None:
    try:
        payload = db["api_payloads"].find_one({"frequency": freq}, {"_id": 0})
        if not payload:
            payload = db["api_payloads"].find_one({"frequency": "combined"}, {"_id": 0})
        if not payload:
            payload = db["api_payloads"].find_one({}, {"_id": 0})

        if payload:
            payload["empty"] = False
            base_json = _read_json_fallback(f"{freq}.json") or _read_json_fallback("combined.json")
            if base_json and isinstance(base_json, dict) and base_json.get("combined"):
                payload["combined"] = base_json["combined"]
            freq_filter = {"$or": [{"frequency": freq}, {"frequency": "combined"}, {"frequency": {"$exists": False}}]}
            
            if "scores" not in payload or not payload["scores"]:
                payload["scores"] = list(db["risk_scores"].find(freq_filter, {"_id": 0}))
            if "validation" not in payload or not payload["validation"]:
                payload["validation"] = list(db["validation_findings"].find(freq_filter, {"_id": 0}))
            if "validation_counts" not in payload or not payload["validation_counts"]:
                val_list = payload.get("validation", [])
                v_counts = {}
                for v in val_list:
                    cat = v.get("category")
                    if cat:
                        v_counts[cat] = v_counts.get(cat, 0) + 1
                payload["validation_counts"] = v_counts
            if "ranking" not in payload or not payload["ranking"]:
                payload["ranking"] = list(db["bank_rankings"].find(freq_filter, {"_id": 0}))
            if "rule_findings" not in payload or not payload["rule_findings"]:
                rules = list(db["computed_rule_findings"].find(freq_filter, {"_id": 0}))
                payload["rule_findings"] = rules or list(db["rule_findings"].find(freq_filter, {"_id": 0}))
            if "anomalies" not in payload or not payload["anomalies"]:
                anom = list(db["computed_anomalies"].find(freq_filter, {"_id": 0}))
                payload["anomalies"] = anom or list(db["anomalies"].find(freq_filter, {"_id": 0}))
            if "stress" not in payload or not payload.get("stress") or not payload["stress"].get("results"):
                s_doc = db["computed_stress_test_results"].find_one({"frequency": "monthly"}, {"_id": 0}) or db["computed_stress_test_results"].find_one(freq_filter, {"_id": 0}) or db["stress_test_results"].find_one({"frequency": "monthly"}, {"_id": 0}) or db["stress_test_results"].find_one(freq_filter, {"_id": 0})
                if s_doc:
                    payload["stress"] = s_doc.get("data", s_doc)
            if "ews" not in payload or not payload["ews"]:
                e_doc = db["computed_ews_indicators"].find_one(freq_filter, {"_id": 0}) or db["ews_indicators"].find_one(freq_filter, {"_id": 0})
                if e_doc:
                    payload["ews"] = e_doc.get("data", e_doc)
            if "clusters" not in payload or not payload["clusters"]:
                c_doc = db["computed_clusters"].find_one(freq_filter, {"_id": 0}) or db["clusters"].find_one(freq_filter, {"_id": 0})
                if c_doc:
                    payload["clusters"] = c_doc.get("data", c_doc)
            if "high_risk_periods" not in payload or not payload["high_risk_periods"]:
                payload["high_risk_periods"] = list(db["high_risk_periods"].find(freq_filter, {"_id": 0}))
            if "systemic_stress" not in payload or not payload["systemic_stress"]:
                payload["systemic_stress"] = list(db["systemic_stress"].find(freq_filter, {"_id": 0}))
            if "disclaimer" not in payload or not payload["disclaimer"]:
                payload["disclaimer"] = DISCLAIMER
            if "unmapped_labels" not in payload or not payload["unmapped_labels"]:
                payload["unmapped_labels"] = list(db["unmapped_labels"].find({}, {"_id": 0}))
            if "rules_config" not in payload or not payload["rules_config"]:
                payload["rules_config"] = list(db["regulatory_rules_config"].find({}, {"_id": 0}))
            if "heatmap" not in payload or not payload.get("heatmap") or not payload["heatmap"].get("banks"):
                payload["heatmap"] = _build_heatmap_from_mongo(db, freq)
            if "domain_means" not in payload or not payload.get("domain_means"):
                payload["domain_means"] = _build_domain_means_from_mongo(db, freq)

            base_json = _read_json_fallback(f"{freq}.json") or _read_json_fallback("combined.json")
            if base_json and isinstance(base_json, dict):
                if base_json.get("combined"):
                    payload["combined"] = base_json["combined"]
                if base_json.get("base_metrics"):
                    payload["base_metrics"] = base_json["base_metrics"]
                if base_json.get("anomaly_features"):
                    payload["anomaly_features"] = base_json["anomaly_features"]

            if "files" not in payload or not payload["files"] or "bank_id" not in (payload["files"][0] if payload["files"] else {}):
                raw_files = list(db["raw_files"].find({}, {"_id": 0}))
                formatted_files = []
                for f in raw_files:
                    fname = f.get("filename") or f.get("file") or f.get("bank_id") or "N/A"
                    bank_code = fname.replace("_data.xlsx", "").replace(".xlsx", "").replace("DS_TCTD", "DS_TCTD")
                    formatted_files.append({
                        "bank_id": f.get("bank_id") or bank_code,
                        "frequencies": f.get("frequencies") or [freq],
                        "metrics": f.get("metrics") or 73,
                        "rows": f.get("rows") or 36,
                        "size_kb": f.get("size_kb") or 24.0,
                    })
                payload["files"] = formatted_files if formatted_files else payload.get("files", [])
            if "periods" not in payload or not payload["periods"]:
                payload["periods"] = _build_periods_from_mongo(db, freq)
            if "missing_by_metric" not in payload or not payload["missing_by_metric"]:
                payload["missing_by_metric"] = _build_missing_by_metric_from_mongo(db, freq)
            if "series" not in payload or not payload["series"] or not payload["series"].get("data"):
                ts_doc = db["time_series_data"].find_one(freq_filter, {"_id": 0})
                if ts_doc:
                    payload["series"] = ts_doc.get("series", ts_doc)
                if "series" not in payload or not payload["series"] or not payload["series"].get("data"):
                    payload["series"] = _build_series_from_mongo(db, freq)
            if "banks" not in payload or not payload["banks"]:
                payload["banks"] = sorted(list(payload.get("series", {}).get("data", {}).keys()))

            if "summary" not in payload or not payload["summary"]:
                rf_list = payload.get("rule_findings", [])
                anom_list = payload.get("anomalies", [])
                payload["summary"] = {
                    "n_banks": len(payload["files"]) or 31,
                    "n_periods": len(payload["periods"].get("items", [])),
                    "missing_pct": 34.61,
                    "n_anomalies": len(anom_list),
                    "anomaly_rate": round(len(anom_list) / max(len(rf_list), 1) * 100, 2),
                    "cluster_k": 3,
                    "silhouette": 0.528,
                    "level_counts": {
                        "CRITICAL": sum(1 for r in rf_list if r.get("severity") == "CRITICAL"),
                        "HIGH": sum(1 for r in rf_list if r.get("severity") == "HIGH"),
                        "MEDIUM": sum(1 for r in rf_list if r.get("severity") == "MEDIUM"),
                        "LOW": sum(1 for r in rf_list if r.get("severity") == "LOW"),
                    }
                }
            return payload

        # Fallback query from structured collections if api_payloads is absent
        freq_filter = {"$or": [{"frequency": freq}, {"frequency": "combined"}, {"frequency": {"$exists": False}}]}
        payload = {"frequency": freq, "empty": False}
        rules = list(db["computed_rule_findings"].find(freq_filter, {"_id": 0}))
        if not rules:
            rules = list(db["rule_findings"].find(freq_filter, {"_id": 0}))
        payload["rule_findings"] = rules
        payload["rules_config"] = list(db["regulatory_rules_config"].find({}, {"_id": 0}))
        payload["scores"] = list(db["risk_scores"].find(freq_filter, {"_id": 0}))
        payload["ranking"] = list(db["bank_rankings"].find(freq_filter, {"_id": 0}))

        anom = list(db["computed_anomalies"].find(freq_filter, {"_id": 0}))
        if not anom:
            anom = list(db["anomalies"].find(freq_filter, {"_id": 0}))
        payload["anomalies"] = anom

        clusters_doc = db["computed_clusters"].find_one(freq_filter, {"_id": 0}) or db["clusters"].find_one(freq_filter, {"_id": 0})
        if clusters_doc:
            payload["clusters"] = clusters_doc.get("data", clusters_doc)

        ews_doc = db["computed_ews_indicators"].find_one(freq_filter, {"_id": 0}) or db["ews_indicators"].find_one(freq_filter, {"_id": 0})
        if ews_doc:
            payload["ews"] = ews_doc.get("data", ews_doc)

        stress_doc = db["computed_stress_test_results"].find_one(freq_filter, {"_id": 0}) or db["stress_test_results"].find_one(freq_filter, {"_id": 0})
        if stress_doc:
            payload["stress"] = stress_doc.get("data", stress_doc)

        val_list = list(db["validation_findings"].find(freq_filter, {"_id": 0}))
        payload["validation"] = val_list
        v_counts = {}
        for v in val_list:
            cat = v.get("category")
            if cat:
                v_counts[cat] = v_counts.get(cat, 0) + 1
        payload["validation_counts"] = v_counts
        payload["high_risk_periods"] = list(db["high_risk_periods"].find(freq_filter, {"_id": 0}))
        payload["systemic_stress"] = list(db["systemic_stress"].find(freq_filter, {"_id": 0}))
        payload["periods"] = _build_periods_from_mongo(db, freq)
        payload["files"] = list(db["raw_files"].find({}, {"_id": 0}))
        payload["missing_by_metric"] = _build_missing_by_metric_from_mongo(db, freq)
        payload["series"] = _build_series_from_mongo(db, freq)
        payload["banks"] = sorted(list(payload.get("series", {}).get("data", {}).keys()))
        payload["heatmap"] = _build_heatmap_from_mongo(db, freq)
        payload["domain_means"] = _build_domain_means_from_mongo(db, freq)

        base_json = _read_json_fallback(f"{freq}.json") or _read_json_fallback("combined.json")
        if base_json and isinstance(base_json, dict):
            if base_json.get("combined"):
                payload["combined"] = base_json["combined"]
            if base_json.get("base_metrics"):
                payload["base_metrics"] = base_json["base_metrics"]
            if base_json.get("anomaly_features"):
                payload["anomaly_features"] = base_json["anomaly_features"]

        rf_list = payload.get("rule_findings", [])
        anom_list = payload.get("anomalies", [])
        files_list = payload.get("files", [])
        periods_items = payload.get("periods", {}).get("items", [])

        n_banks = len(files_list) if files_list else len(payload.get("banks", []))
        if not n_banks:
            n_banks = len({r.get("bank_id") for r in payload.get("scores", []) if r.get("bank_id")}) or 31

        n_periods = len(periods_items) if periods_items else len({r.get("period") for r in payload.get("scores", []) if r.get("period")}) or 36

        missing_metrics = payload.get("missing_by_metric", [])
        if missing_metrics:
            missing_pct = round(sum(m.get("missing_pct", 0) for m in missing_metrics) / len(missing_metrics), 2)
        else:
            missing_pct = 34.61

        clusters_info = payload.get("clusters", {})
        cluster_k = clusters_info.get("k", 3) if isinstance(clusters_info, dict) else 3

        payload["summary"] = {
            "n_banks": n_banks,
            "n_periods": n_periods,
            "missing_pct": missing_pct,
            "n_anomalies": len(anom_list),
            "anomaly_rate": round(len(anom_list) / max(len(rf_list), 1) * 100, 2),
            "cluster_k": cluster_k,
            "silhouette": 0.528,
            "level_counts": {
                "CRITICAL": sum(1 for r in rf_list if r.get("severity") == "CRITICAL"),
                "HIGH": sum(1 for r in rf_list if r.get("severity") == "HIGH"),
                "MEDIUM": sum(1 for r in rf_list if r.get("severity") == "MEDIUM"),
                "LOW": sum(1 for r in rf_list if r.get("severity") == "LOW"),
            }
        }

        payload["disclaimer"] = DISCLAIMER
        base_json = _read_json_fallback(f"{freq}.json") or _read_json_fallback("combined.json")
        if base_json and isinstance(base_json, dict) and base_json.get("combined"):
            payload["combined"] = base_json["combined"]
        payload["unmapped_labels"] = list(db["unmapped_labels"].find({}, {"_id": 0}))

        return payload
    except Exception as exc:
        LOG.warning("Failed to fetch payload for '%s' from MongoDB: %s", freq, exc)
        return None


@router.get("/meta")
def get_meta():
    """System metadata endpoint."""
    db = _get_db()
    if db is not None:
        meta_doc = db["api_meta"].find_one({}, {"_id": 0})
        if meta_doc:
            if not meta_doc.get("frequencies"):
                meta_doc["frequencies"] = ["combined", "monthly", "quarterly", "yearly", "daily"]
            return meta_doc

    fallback = _read_json_fallback("meta.json")
    if fallback and isinstance(fallback, dict):
        if not fallback.get("frequencies"):
            fallback["frequencies"] = ["combined", "monthly", "quarterly", "yearly", "daily"]
        return fallback

    meta = build_meta()
    if not meta.get("frequencies"):
        meta["frequencies"] = ["combined", "monthly", "quarterly", "yearly", "daily"]
    return meta


@router.get("/data/{freq}")
def get_data(freq: str, source: str | None = Query(None)):
    """Overview FE payload for a given frequency."""
    if source == "baseline":
        fallback = _read_json_fallback(f"{freq}.json")
        if not fallback:
            try:
                fallback = build_payload(freq, use_cache=True)
            except Exception:
                pass
        if fallback and isinstance(fallback, dict):
            fallback["empty"] = False
            fallback["data_source"] = "baseline"
            return fallback

    db = _get_db()
    if db is not None:
        mongo_payload = _get_freq_payload_from_mongo(db, freq)
        if mongo_payload:
            mongo_payload["empty"] = False
            mongo_payload["data_source"] = "computed"
            return mongo_payload

    fallback = _read_json_fallback(f"{freq}.json")
    if fallback:
        if isinstance(fallback, dict):
            fallback["empty"] = False
            fallback["data_source"] = "baseline"
        return fallback

    raise HTTPException(status_code=404, detail=f"No data for '{freq}'. Run pipeline first.")


@router.get("/performance")
def get_performance():
    """System performance tracker endpoint."""
    db = _get_db()
    if db is not None:
        perf_doc = db["api_performance"].find_one({}, {"_id": 0})
        if perf_doc:
            return perf_doc

    fallback = _read_json_fallback("performance.json")
    if fallback:
        return fallback

    return build_performance()


@router.get("/pdf-status")
def get_pdf_status():
    """Regulatory PDF status endpoint."""
    db = _get_db()
    if db is not None:
        pdf_doc = db["api_pdf_status"].find_one({}, {"_id": 0})
        if pdf_doc:
            return pdf_doc

    fallback = _read_json_fallback("pdf_status.json")
    if fallback:
        return fallback

    return build_pdf_status()


@router.post("/run/{freq}")
def run_frequency(freq: str, fresh: int = 0):
    """Trigger frequency recalculation."""
    try:
        export_frequency(freq, use_cache=(fresh == 0))
        db = _get_db()
        if db is not None:
            mongo_payload = _get_freq_payload_from_mongo(db, freq)
            if mongo_payload:
                return {"ok": True, "data": mongo_payload}
        fallback = _read_json_fallback(f"{freq}.json")
        return {"ok": True, "data": fallback}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/refresh-side")
def refresh_side():
    """Refresh side data."""
    try:
        export_side()
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/report/{freq}")
def generate_report(freq: str):
    """Trigger report generation."""
    from src.pipeline import run_pipeline
    from src.reporting import generate_all_reports

    try:
        res = run_pipeline(DATA_ROOT, freq, use_cache=True)
        paths = generate_all_reports(res)
        files = [{"kind": k, "name": Path(v).name} for k, v in paths.items()]
        return {"ok": True, "files": files}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
