"""Tests for cross-frequency integration (as-of enrichment, no look-ahead)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.multi_frequency import build_combined_wide, source_map_table


def _wide(freq, periods, metrics):
    rows = []
    for bid in ("A", "B"):
        for p, ts in periods:
            row = {"bank_id": bid, "bank_name": bid, "period": p,
                   "period_ts": pd.Timestamp(ts)}
            row.update({m: v for m, v in metrics(bid, p).items()})
            rows.append(row)
    return pd.DataFrame(rows)


def _build_wide_dict():
    months = [(f"2024-{m:02d}", f"2024-{m:02d}-28") for m in range(1, 13)]
    quarters = [("2024Q1", "2024-03-31"), ("2024Q2", "2024-06-30"),
                ("2024Q3", "2024-09-30"), ("2024Q4", "2024-12-31")]
    # Prior-year annual (2023) so Jan–Nov 2024 have an as-of value within tolerance.
    years = [("2023", "2023-12-31"), ("2024", "2024-12-31")]
    monthly = _wide("monthly", months, lambda b, p: {"ldr": 80.0, "car_solo": 11.0})
    # Quarterly carries an asset-quality metric not present monthly.
    quarterly = _wide("quarterly", quarters,
                      lambda b, p: {"npl_ratio": 2.0 + int(p[-1]), "customer_loans": 1000.0})
    # Yearly carries profitability not present monthly/quarterly.
    yearly = _wide("yearly", years, lambda b, p: {"roa": 1.2, "nim": 3.0})
    return {"monthly": monthly, "quarterly": quarterly, "yearly": yearly}


def test_combined_adds_coarser_metrics():
    wide = _build_wide_dict()
    combined = build_combined_wide(wide, {"multi_frequency": {"enabled": True}})
    assert combined is not None
    # Monthly grain preserved.
    assert len(combined) == 24  # 2 banks × 12 months
    # Quarter-only and year-only metrics now present on the monthly grain.
    for m in ("npl_ratio", "customer_loans", "roa", "nim"):
        assert m in combined.columns
    assert combined["roa"].notna().all()        # yearly value carried across months


def test_as_of_is_backward_no_lookahead():
    wide = _build_wide_dict()
    combined = build_combined_wide(wide, {})
    a = combined[combined["bank_id"] == "A"].sort_values("period_ts")
    # 2024-02 is before 2024Q1's period_ts (2024-03-31) -> NPL still NaN (no look-ahead).
    feb = a[a["period"] == "2024-02"]["npl_ratio"].iloc[0]
    assert pd.isna(feb)
    # 2024-04 is after 2024Q1 close -> gets Q1 NPL (2 + 1 = 3).
    apr = a[a["period"] == "2024-04"]["npl_ratio"].iloc[0]
    assert apr == 3.0


def test_source_map_records_provenance():
    wide = _build_wide_dict()
    combined = build_combined_wide(wide, {})
    smt = source_map_table(combined)
    prim = dict(zip(smt["metric"], smt["primary_frequency"]))
    assert prim["ldr"] == "monthly"
    assert prim["npl_ratio"] == "quarterly"
    assert prim["roa"] == "yearly"


def test_none_when_no_coarser():
    wide = {"monthly": _build_wide_dict()["monthly"]}
    assert build_combined_wide(wide, {}) is None
