"""FastAPI Router for Raw Financial Panel Data & Metadata.

Reads raw panel data & metadata from MongoDB 'bank_risk_db'
(collections: 'raw_panel_data', 'raw_files', 'unmapped_labels').
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pymongo import MongoClient

router = APIRouter(prefix="/api/raw", tags=["Raw Financial Data"])

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


@router.get("/files")
def get_raw_files():
    """Fetch raw input file metadata."""
    db = _get_db()
    if db is not None:
        try:
            items = list(db["raw_files"].find({}, {"_id": 0}))
            if items:
                return {"ok": True, "count": len(items), "files": items}
        except Exception:
            pass

    payload = _read_fallback_json("combined")
    files = (payload or {}).get("files", [])
    return {"ok": True, "count": len(files), "files": files}


@router.get("/panel-data")
def get_raw_panel_data(
    bank_id: str | None = None,
    period: str | None = None,
    frequency: str | None = None,
    limit: int = 1000,
):
    """Query raw financial panel records from MongoDB 'raw_panel_data' collection."""
    db = _get_db()
    if db is not None:
        try:
            query: dict[str, Any] = {}
            if bank_id:
                query["bank_id"] = bank_id
            if period:
                query["period"] = period
            if frequency:
                query["frequency"] = frequency

            items = list(db["raw_panel_data"].find(query, {"_id": 0}).limit(limit))
            return {"ok": True, "count": len(items), "data": items}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    return {"ok": True, "count": 0, "data": []}
