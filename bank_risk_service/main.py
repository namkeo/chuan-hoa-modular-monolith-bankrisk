"""FastAPI REST Application & API Gateway for Bank Risk Service.

Entry point connecting all modular APIRouters to MongoDB bank_risk_db (Port 8000).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

# Ensure service root and project root are in sys.path
SERVICE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SERVICE_ROOT.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bank_risk_service.routers import (
    overview_router,
    rule_router,
    ml_router,
    ews_stress_router,
    data_router,
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27017/")
DB_NAME = "bank_risk_db"

app = FastAPI(
    title="Bank Risk Analysis API Gateway & Dynamic Processing Service",
    description="FastAPI Server serving Bank Risk Analysis data & processing directly from MongoDB",
    version="1.0.0",
)

# Enable CORS for React UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register modular routers
app.include_router(overview_router.router)
app.include_router(rule_router.router)
app.include_router(ml_router.router)
app.include_router(ews_stress_router.router)
app.include_router(data_router.router)


@app.get("/api/health", tags=["System Gateway"])
def health_check():
    """Health check endpoint."""
    mongo_connected = False
    connected_uri = MONGO_URI
    uris = []
    if os.getenv("MONGO_URI"):
        uris.append(os.getenv("MONGO_URI"))
    uris.extend(["mongodb://admin:12345678@localhost:27018/", "mongodb://admin:12345678@localhost:27017/"])
    for uri in uris:
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=1500)
            client.admin.command("ping")
            mongo_connected = True
            connected_uri = uri
            break
        except Exception:
            continue

    return {
        "ok": True,
        "service": "bank_risk_service",
        "python": sys.executable,
        "mongoConnected": mongo_connected,
        "mongoUri": connected_uri,
        "database": DB_NAME,
    }


if __name__ == "__main__":
    print(f"Starting Bank Risk Service API Gateway on http://localhost:8000 (MongoDB: {MONGO_URI})")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
