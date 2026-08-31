"""FastAPI Router for Legal Rule Monitoring (Giám sát rule pháp lý NHNN).

Reads raw panel data & rule configurations from MongoDB 'bank_risk_db'
(collections: 'rule_findings', 'regulatory_rules_config', 'raw_panel_data').
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pymongo import MongoClient

router = APIRouter(prefix="/api/rule-findings", tags=["Rule Monitor"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
API_DIR = PROJECT_ROOT / "outputs" / "api"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27017/")
DB_NAME = "bank_risk_db"


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


def _read_fallback_json(frequency: str) -> dict | None:
    fpath = API_DIR / f"{frequency}.json"
    if fpath.exists():
        try:
            return json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


@router.get("/filter")
def filter_rule_findings(
    frequency: str = "combined",
    bank_id: str | None = None,
    period: str | None = None,
    rule_name: str | None = None,
    metric: str | None = None,
    severity: str | None = None,
    finding_type: str | None = None,
    legal_source: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
):
    """Filter legal rule violation findings directly from MongoDB 'rule_findings' collection."""
    db = _get_db()
    if db is not None:
        try:
            coll = db["computed_rule_findings"]
            if coll.count_documents({}) == 0:
                coll = db["rule_findings"]
            query: dict[str, Any] = {}
            if frequency:
                query["frequency"] = frequency
            if bank_id:
                banks = [b.strip() for b in bank_id.split(",") if b.strip()]
                query["bank_id"] = banks[0] if len(banks) == 1 else {"$in": banks}
            if period:
                query["period"] = period
            if rule_name:
                query["rule_name"] = {"$regex": rule_name, "$options": "i"}
            if metric:
                query["metric"] = metric
            if severity:
                sevs = [s.strip().upper() for s in severity.split(",") if s.strip()]
                query["severity"] = sevs[0] if len(sevs) == 1 else {"$in": sevs}
            if finding_type:
                query["finding_type"] = finding_type
            if legal_source:
                query["legal_source"] = {"$regex": legal_source, "$options": "i"}

            if min_value is not None or max_value is not None:
                val_q: dict[str, Any] = {}
                if min_value is not None:
                    val_q["$gte"] = min_value
                if max_value is not None:
                    val_q["$lte"] = max_value
                query["metric_value"] = val_q

            results = list(coll.find(query, {"_id": 0}))

            base_q = {"frequency": frequency} if frequency else {}
            distinct_banks = sorted([b for b in coll.distinct("bank_id", base_q) if b])
            distinct_periods = sorted([p for p in coll.distinct("period", base_q) if p])
            distinct_rules = sorted([r for r in coll.distinct("rule_name", base_q) if r])
            distinct_metrics = sorted([m for m in coll.distinct("metric", base_q) if m])
            distinct_severities = sorted([s for s in coll.distinct("severity", base_q) if s])
            distinct_types = sorted([t for t in coll.distinct("finding_type", base_q) if t])
            distinct_sources = sorted([src for src in coll.distinct("legal_source", base_q) if src])

            return {
                "ok": True,
                "total": len(results),
                "findings": results,
                "filter_options": {
                    "banks": distinct_banks,
                    "periods": distinct_periods,
                    "rules": distinct_rules,
                    "metrics": distinct_metrics,
                    "severities": distinct_severities,
                    "finding_types": distinct_types,
                    "legal_sources": distinct_sources,
                },
            }
        except Exception as exc:
            pass

    # Static JSON Fallback filtering
    payload = _read_fallback_json(frequency)
    findings = (payload or {}).get("rule_findings", [])
    if bank_id:
        banks = [b.strip() for b in bank_id.split(",") if b.strip()]
        findings = [f for f in findings if f.get("bank_id") in banks]
    if period:
        findings = [f for f in findings if f.get("period") == period]
    if rule_name:
        findings = [f for f in findings if rule_name.lower() in str(f.get("rule_name", "")).lower()]
    if metric:
        findings = [f for f in findings if f.get("metric") == metric]
    if severity:
        sevs = [s.strip().upper() for s in severity.split(",") if s.strip()]
        findings = [f for f in findings if str(f.get("severity", "")).upper() in sevs]
    if finding_type:
        findings = [f for f in findings if f.get("finding_type") == finding_type]
    if legal_source:
        findings = [f for f in findings if legal_source.lower() in str(f.get("legal_source", "")).lower()]

    all_findings = (payload or {}).get("rule_findings", [])
    return {
        "ok": True,
        "total": len(findings),
        "findings": findings,
        "filter_options": {
            "banks": sorted(list({f.get("bank_id") for f in all_findings if f.get("bank_id")})),
            "periods": sorted(list({f.get("period") for f in all_findings if f.get("period")})),
            "rules": sorted(list({f.get("rule_name") for f in all_findings if f.get("rule_name")})),
            "metrics": sorted(list({f.get("metric") for f in all_findings if f.get("metric")})),
            "severities": sorted(list({f.get("severity") for f in all_findings if f.get("severity")})),
            "finding_types": sorted(list({f.get("finding_type") for f in all_findings if f.get("finding_type")})),
            "legal_sources": sorted(list({f.get("legal_source") for f in all_findings if f.get("legal_source")})),
        },
    }
