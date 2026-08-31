"""FastAPI Router for Machine Learning (Phát hiện bất thường Isolation Forest, Phân cụm K-Means & Tinh chỉnh mô hình).

Reads raw panel data & model parameters from MongoDB 'bank_risk_db'
(collections: 'anomalies', 'clusters', 'computed_anomalies', 'computed_clusters').
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pymongo import MongoClient

router = APIRouter(prefix="/api", tags=["Machine Learning & Tuning"])

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


@router.get("/ml/anomalies/{frequency}")
def get_anomalies(frequency: str = "combined"):
    """Fetch Isolation Forest anomaly detection findings for a given frequency."""
    db = _get_db()
    if db is not None:
        try:
            items = list(db["computed_anomalies"].find({"frequency": frequency}, {"_id": 0}))
            if not items:
                items = list(db["anomalies"].find({"frequency": frequency}, {"_id": 0}))
            if items:
                return {"ok": True, "frequency": frequency, "count": len(items), "anomalies": items}
        except Exception:
            pass

    payload = _read_fallback_json(frequency)
    anomalies = (payload or {}).get("anomalies", [])
    return {"ok": True, "frequency": frequency, "count": len(anomalies), "anomalies": anomalies}


@router.get("/ml/clusters/{frequency}")
def get_clusters(frequency: str = "combined"):
    """Fetch K-Means clustering profiles & projections for a given frequency."""
    db = _get_db()
    if db is not None:
        try:
            doc = db["computed_clusters"].find_one({"frequency": frequency}, {"_id": 0})
            if not doc:
                doc = db["clusters"].find_one({"frequency": frequency}, {"_id": 0})
            if doc:
                return {"ok": True, "frequency": frequency, "clusters": doc}
        except Exception:
            pass

    payload = _read_fallback_json(frequency)
    clusters = (payload or {}).get("clusters", {})
    return {"ok": True, "frequency": frequency, "clusters": clusters}


@router.post("/tune/{frequency}")
def tune_model(frequency: str, model: str = "isolation_forest", criterion: str = "auto"):
    """Run hyper-parameter tuning for Isolation Forest or K-Means."""
    from src.hyperparameter_tuning import auto_tune

    try:
        res = auto_tune(frequency=frequency, model_type=model, criterion=criterion)
        return {"ok": True, "tuning": res}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tune/apply")
def apply_tuning(params: dict[str, Any]):
    """Apply tuned model parameters to current session."""
    from src.hyperparameter_tuning import apply_tuned_params

    try:
        apply_tuned_params(params)
        return {"ok": True, "applied": params}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tune/reset")
def reset_tuning():
    """Reset model parameters to defaults."""
    from src.hyperparameter_tuning import reset_params

    try:
        reset_params()
        return {"ok": True, "reset": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
