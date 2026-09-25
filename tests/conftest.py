"""Shared pytest fixtures: a small synthetic wide bank-period table so unit tests
run fast and deterministically without depending on the real Excel files."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

warnings.filterwarnings("ignore")

# Các test import `src.*`, mà package `src` nằm trong bank_risk_service/ (từ lần
# refactor dọn thư mục gốc). Chỉ thêm project root là chưa đủ — phải thêm cả
# service root, nếu không toàn bộ test không collect được.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "bank_risk_service"))


@pytest.fixture()
def synthetic_wide() -> pd.DataFrame:
    """4 banks × 8 quarterly periods with the canonical ratio columns.

    BANK_D is engineered to breach mandatory legal limits (CAR < 8, LDR > 85,
    liquidity reserve < 10) so rule/score tests have a deterministic CRITICAL.
    """
    periods = pd.period_range("2023Q1", periods=8, freq="Q")
    rows = []
    rng = np.random.default_rng(0)
    profiles = {
        "BANK_A": dict(car=14, ldr=70, npl=1.2, res=18, roa=1.4),   # healthy
        "BANK_B": dict(car=11, ldr=80, npl=2.5, res=13, roa=0.9),   # ok
        "BANK_C": dict(car=9.5, ldr=84, npl=3.5, res=11, roa=0.4),  # watch
        "BANK_D": dict(car=6.5, ldr=92, npl=6.0, res=8, roa=-0.3),  # breach
    }
    for bid, p in profiles.items():
        for i, per in enumerate(periods):
            jitter = rng.normal(0, 0.05)
            ts = per.to_timestamp(how="end").normalize()
            rows.append({
                "bank_id": bid, "bank_name": bid, "period": str(per),
                "period_ts": pd.Timestamp(ts),
                "car_solo": p["car"] + jitter,
                "ldr": p["ldr"] + jitter,
                "npl_ratio": p["npl"] + jitter,
                "group2_ratio": p["npl"] * 0.8 + jitter,
                "liquidity_reserve_ratio": p["res"] + jitter,
                "st_funding_for_mlt_loans": 25 + i * 0.5 + jitter,
                "roa": p["roa"] + jitter,
                "roe": p["roa"] * 9 + jitter,
                "llr_coverage": 80 - p["npl"] * 5 + jitter,
                "cir": 50 + p["npl"] + jitter,
                "total_assets": 100000 + i * 1000,
                "equity": 9000 + i * 50,
                "customer_loans": 70000 + i * 800,
                "deposits": 85000 + i * 600,
            })
    return pd.DataFrame(rows)
