"""FastAPI Router for Early Warning System (EWS) & Stress Testing.

Reads raw panel data & indicator calculations from MongoDB 'bank_risk_db'
(collections: 'ews_indicators', 'stress_test_results', 'raw_panel_data').
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pymongo import MongoClient

router = APIRouter(prefix="/api/analytics", tags=["EWS & Stress Testing"])

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


@router.get("/ews/{frequency}")
def get_ews(frequency: str = "combined"):
    """Fetch Early Warning System (EWS) indicator trajectory & warning levels."""
    db = _get_db()
    if db is not None:
        try:
            doc = db["computed_ews_indicators"].find_one({"frequency": frequency}, {"_id": 0})
            if not doc:
                doc = db["ews_indicators"].find_one({"frequency": frequency}, {"_id": 0})
            if doc:
                return {"ok": True, "frequency": frequency, "ews": doc}
        except Exception:
            pass

    payload = _read_fallback_json(frequency)
    ews = (payload or {}).get("ews", {})
    return {"ok": True, "frequency": frequency, "ews": ews}


@router.get("/stress/{frequency}")
def get_stress_test(frequency: str = "combined"):
    """Fetch Stress Testing scenarios, system impacts, and breaking points."""
    db = _get_db()
    if db is not None:
        try:
            doc = db["computed_stress_test_results"].find_one({"frequency": frequency}, {"_id": 0})
            if not doc:
                doc = db["stress_test_results"].find_one({"frequency": frequency}, {"_id": 0})
            if doc:
                return {"ok": True, "frequency": frequency, "stress": doc}
        except Exception:
            pass

    payload = _read_fallback_json(frequency)
    stress = (payload or {}).get("stress", {})
    return {"ok": True, "frequency": frequency, "stress": stress}
