"""Tests for data ingestion: period parsing, alias mapping, real-folder smoke."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_loader import (bank_from_filename, build_alias_lookup,
                             build_wide_tables, load_all, metric_label_lookup,
                             missing_metric_table, parse_period)
from src.utils import DATA_ROOT, load_config

# Bank input files live in the resolved data folder (e.g. ../data_all), which is
# kept separate from the source tree — use DATA_ROOT, not the project root.
ROOT = DATA_ROOT


def test_parse_period_variants():
    assert parse_period("Q1/2023", "quarterly")[0] == "2023Q1"
    assert parse_period("T03/2023", "monthly")[0] == "2023-03"
    assert parse_period("31/12/2023", "daily")[0] == "2023-12-31"
    assert parse_period("2023", "yearly")[0] == "2023"
    assert parse_period("không phải kỳ", "monthly")[0] is None


def test_bank_from_filename():
    bid, name = bank_from_filename(Path("ACB_data.xlsx"))
    assert bid == "ACB"
    bid2, _ = bank_from_filename(Path("Vietcombank_data.xlsx"))
    assert bid2 == "VIETCOMBANK"


def test_alias_lookup_built():
    cfg = load_config("column_mapping")
    lookup = build_alias_lookup(cfg)
    assert lookup  # non-empty
    # A known alias resolves to its canonical name.
    assert any(v == "npl_ratio" for v in lookup.values())


def test_build_wide_tables_from_panel():
    panel = pd.DataFrame({
        "bank_id": ["A", "A"], "bank_name": ["A", "A"],
        "period": ["2023Q1", "2023Q1"], "period_ts": pd.to_datetime(["2023-03-31"] * 2),
        "frequency": ["quarterly", "quarterly"],
        "metric_name": ["npl_ratio", "ldr"], "metric_value": [2.0, 80.0],
    })
    wide = build_wide_tables(panel)
    assert "quarterly" in wide
    assert {"npl_ratio", "ldr"}.issubset(wide["quarterly"].columns)


def _panel_with_labels() -> pd.DataFrame:
    return pd.DataFrame({
        "bank_id": ["A", "A"], "bank_name": ["A", "A"],
        "period": ["2023-01", "2023-02"],
        "period_ts": pd.to_datetime(["2023-01-31", "2023-02-28"]),
        "frequency": ["monthly", "monthly"],
        "metric_name": ["group2_ratio", "group2_ratio"],
        "metric_label": ["Tỷ lệ nợ nhóm 2", "Tỷ lệ nợ nhóm 2"],
        "unit": ["%", "%"], "camels_group": ["A", "A"],
        "metric_value": [3.2, 3.6],
    })


def test_metric_label_lookup_prefers_source_label():
    lookup = metric_label_lookup(_panel_with_labels(), load_config("column_mapping"))
    assert lookup["group2_ratio"]["label"] == "Tỷ lệ nợ nhóm 2"
    assert lookup["group2_ratio"]["is_derived_ratio"] is False


def test_missing_metric_table_drops_derived_variants():
    """Bảng chỉ tiêu thiếu chỉ liệt kê chỉ tiêu gốc, không liệt kê biến phái sinh."""
    feats = pd.DataFrame({
        "bank_id": ["A", "A"], "bank_name": ["A", "A"],
        "period": ["2023-01", "2023-02"],
        "period_ts": pd.to_datetime(["2023-01-31", "2023-02-28"]),
        "group2_ratio": [3.2, None],          # 1/2 thiếu -> phải có trong bảng
        "group2_ratio__qoq": [None, None],    # biến phái sinh -> phải bị loại
        "group2_ratio__yoy": [None, None],
        "systemic_stress_index": [None, None],  # cột hệ thống -> phải bị loại
        "ldr": [80.0, 82.0],                  # không thiếu -> không liệt kê
    })
    out = missing_metric_table(feats, _panel_with_labels(),
                               load_config("column_mapping"))
    assert list(out["metric"]) == ["group2_ratio"]
    row = out.iloc[0]
    assert row["label"] == "Tỷ lệ nợ nhóm 2"
    assert row["n_missing"] == 1 and row["n_total"] == 2
    assert abs(row["missing_pct"] - 50.0) < 1e-6


def test_load_all_real_folder_smoke():
    res = load_all(ROOT, use_cache=True)
    assert not res.panel.empty
    assert res.panel["bank_id"].nunique() >= 5
    # Multiple frequencies should be detected.
    assert len(res.wide) >= 2
