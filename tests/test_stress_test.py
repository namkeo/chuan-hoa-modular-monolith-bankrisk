"""Tests for the stress-test engine: capital shock, shortfall, reverse stress."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.stress_test import (_apply_capital, _breaking_point_npl, _derive_inputs,
                             run_stress_test)


def _row(**kw):
    base = {"bank_id": "B", "bank_name": "B", "period": "2025-12",
            "period_ts": pd.Timestamp("2025-12-31")}
    base.update(kw)
    return pd.Series(base)


def test_derive_rwa_from_car():
    inp = _derive_inputs(_row(own_capital_solo=120.0, car_solo=12.0,
                              customer_loans=800.0, npl_ratio=2.0, deposits=900.0))
    # RWA = own / (CAR/100) = 120 / 0.12 = 1000.
    assert abs(inp["rwa"] - 1000.0) < 1e-6
    assert "capital" not in inp["data_gaps"]
    # npl_amount derived from loans × ratio.
    assert abs(inp["npl_amount"] - 16.0) < 1e-6


def test_implausible_car_flagged_data_gap():
    inp = _derive_inputs(_row(car_solo=0.0, own_capital_solo=100.0,
                              customer_loans=500.0, npl_ratio=2.0, deposits=600.0))
    assert "capital" in inp["data_gaps"]


def test_capital_shock_reduces_car():
    inp = _derive_inputs(_row(own_capital_solo=120.0, car_solo=12.0,
                              customer_loans=1000.0, npl_ratio=2.0, deposits=1100.0))
    sc = {"npl_shock_pp": 5.0, "rwa_shock": 0.0, "lgd": 0.5}
    out = _apply_capital(inp, sc, min_car=8.0, default_lgd=0.55)
    assert out["capital_status"] == "OK"
    # loss = loans(1000) × 5% × 0.5 = 25 -> own 120->95, RWA 1000 -> CAR 9.5%.
    assert abs(out["stressed_car"] - 9.5) < 0.01
    assert out["stressed_car"] < out["baseline_car"]
    assert out["passes_capital"] is True  # 9.5 >= 8


def test_capital_shortfall_when_breached():
    inp = _derive_inputs(_row(own_capital_solo=90.0, car_solo=9.0,
                              customer_loans=1000.0, npl_ratio=2.0, deposits=1100.0))
    sc = {"npl_shock_pp": 6.0, "rwa_shock": 0.0, "lgd": 0.6}
    out = _apply_capital(inp, sc, min_car=8.0, default_lgd=0.55)
    # loss = 1000×6%×0.6 = 36 -> own 90->54, RWA 1000 -> CAR 5.4% < 8.
    assert out["passes_capital"] is False
    assert out["capital_shortfall"] > 0  # 80 - 54 = 26


def test_breaking_point_npl_reverse_stress():
    inp = _derive_inputs(_row(own_capital_solo=120.0, car_solo=12.0,
                              customer_loans=1000.0, npl_ratio=2.0, deposits=1100.0))
    bp = _breaking_point_npl(inp, min_car=8.0, default_lgd=0.5)
    # buffer = own(120) - 0.08×RWA(1000)=80 -> 40; pp = 40/(1000×0.5)×100 = 8.0.
    assert abs(bp["breaking_npl_pp"] - 8.0) < 0.01
    assert bp["already_below"] is False


def test_run_stress_test_end_to_end():
    rows = []
    for i, bid in enumerate(["A", "B", "C"]):
        rows.append(_row(bank_id=bid, bank_name=bid,
                         own_capital_solo=100 + i * 10, car_solo=9 + i,
                         customer_loans=900.0, npl_ratio=2.0, deposits=1000.0).to_dict())
    feats = pd.DataFrame(rows)
    res = run_stress_test(feats, "monthly")
    assert not res.results.empty
    assert not res.system.empty
    # Every scenario assessed for each bank.
    assert res.results["scenario_id"].nunique() == len(res.scenarios)
    # Severe scenario should be at least as harsh as baseline (more/equal fails).
    sev = res.system[res.system["scenario_id"] == "severe"]["n_fail_capital"].iloc[0]
    base = res.system[res.system["scenario_id"] == "baseline"]["n_fail_capital"].iloc[0]
    assert sev >= base
