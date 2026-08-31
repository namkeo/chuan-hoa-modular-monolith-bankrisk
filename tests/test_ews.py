"""Tests for the Early Warning System: proximity, levels, projection, escalation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.ews import _level_from_score, _proximity, compute_ews


def test_proximity_higher_safer():
    # CAR limit 8, buffer 1.5: safe at >=9.5, max danger at/under 8.
    assert _proximity(9.5, 8.0, 1.5, "higher_safer") == 0.0
    assert _proximity(8.0, 8.0, 1.5, "higher_safer") == 1.0
    assert 0 < _proximity(8.75, 8.0, 1.5, "higher_safer") < 1
    assert _proximity(7.0, 8.0, 1.5, "higher_safer") == 1.0  # breached -> clipped 1


def test_proximity_lower_safer():
    # LDR limit 85, buffer 5: safe at <=80, danger as it rises.
    assert _proximity(80.0, 85.0, 5.0, "lower_safer") == 0.0
    assert _proximity(85.0, 85.0, 5.0, "lower_safer") == 1.0
    assert 0 < _proximity(82.5, 85.0, 5.0, "lower_safer") < 1


def test_level_escalation_floors():
    esc = {"near_limit_min_level": "WATCH", "breached_min_level": "WARNING",
           "breached_worsening_min_level": "ALARM", "projected_breach_periods": 3}
    # Low score but inside buffer -> at least WATCH.
    lvl, _ = _level_from_score(5, esc, any_in_buffer=True, any_breached=False,
                               adverse_trend=False, proj_periods=None)
    assert lvl == "WATCH"
    # Breached + worsening -> ALARM regardless of score.
    lvl, _ = _level_from_score(10, esc, any_in_buffer=True, any_breached=True,
                               adverse_trend=True, proj_periods=None)
    assert lvl == "ALARM"
    # Imminent projected breach -> at least WARNING.
    lvl, _ = _level_from_score(10, esc, any_in_buffer=False, any_breached=False,
                               adverse_trend=False, proj_periods=2)
    assert lvl in ("WARNING", "ALARM")


def _declining_car_panel():
    """One bank whose CAR declines steadily toward the 8% limit over 8 months."""
    periods = pd.period_range("2024-01", periods=8, freq="M")
    rows = []
    car = 11.0
    for per in periods:
        rows.append({
            "bank_id": "BANK_X", "bank_name": "BANK_X", "period": str(per),
            "period_ts": per.to_timestamp(how="end").normalize(),
            "car_solo": car, "ldr": 70.0, "npl_ratio": 2.0,
        })
        car -= 0.4  # steady deterioration
    return pd.DataFrame(rows)


def test_compute_ews_projects_breach():
    panel = _declining_car_panel()
    res = compute_ews(panel, "monthly")
    assert not res.table.empty
    assert "car_solo" in res.metrics_used
    latest = res.latest.iloc[0]
    # CAR trending down toward 8 -> a finite projected breach horizon should appear.
    proj = res.table[res.table["projected_periods_to_breach"].notna()]
    assert not proj.empty
    # EWS score rises over time as CAR approaches the limit.
    series = res.table.sort_values("period_ts")["ews_score"].to_numpy()
    assert series[-1] >= series[0]


def test_compute_ews_levels_and_system():
    panel = _declining_car_panel()
    res = compute_ews(panel, "monthly")
    assert set(res.latest["ews_level"]).issubset({"NORMAL", "WATCH", "WARNING", "ALARM"})
    assert not res.system.empty
    assert {"period", "system_level", "share_warning_plus"}.issubset(res.system.columns)


def test_plausible_filter_drops_garbage():
    # An implausible LDR (e.g. 1995%) must be ignored, not drive an alarm.
    periods = pd.period_range("2024-01", periods=6, freq="M")
    rows = [{"bank_id": "B", "bank_name": "B", "period": str(p),
             "period_ts": p.to_timestamp(how="end").normalize(),
             "ldr": 1995.0, "car_solo": 12.0} for p in periods]
    res = compute_ews(pd.DataFrame(rows), "monthly")
    latest = res.latest.iloc[0]
    # LDR garbage filtered -> not counted as breached.
    assert latest["n_breached"] == 0
