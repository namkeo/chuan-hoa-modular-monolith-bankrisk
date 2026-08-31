"""Tests for validation: khoảng hợp lý, data gap pháp lý theo loại hình, chỉ tiêu
không đánh giá được."""
from __future__ import annotations

import pandas as pd

from src.feature_engineering import GAP_COLUMNS, build_features, derive_ratios
from src.validation import _legal_metric_scope, validate_features


def _features(**metrics) -> pd.DataFrame:
    n = len(next(iter(metrics.values())))
    return pd.DataFrame({
        "bank_id": ["CTTC_MIRAE_ASSET"] * n, "bank_name": ["Mirae"] * n,
        "period": [f"2023-{m:02d}" for m in range(1, n + 1)],
        "period_ts": pd.date_range("2023-01-31", periods=n, freq="ME"),
        **metrics,
    })


def test_legal_metric_scope_excludes_finance_companies_from_ldr():
    """QĐ 682 để trống ô LDR của công ty tài chính/cho thuê tài chính."""
    scope = _legal_metric_scope()
    assert "cong_ty_tai_chinh" not in scope["ldr"]
    assert "cong_ty_cho_thue_tai_chinh" not in scope["ldr"]
    assert "nhtm_co_phan" in scope["ldr"]
    # Rule ngưỡng phẳng (không theo loại hình) vẫn áp cho mọi đơn vị.
    assert scope["npl_ratio"] is None


def test_missing_ldr_is_not_a_data_gap_for_a_finance_company():
    """Chỉ tiêu không áp cho loại hình thì thiếu số KHÔNG phải data gap pháp lý.

    Nếu không, việc bỏ LDR bịa của công ty tài chính lại sinh ra một loạt cờ
    CRITICAL mới — đổi một con số sai lấy một cảnh báo sai.
    """
    feats = _features(ldr=[float("nan")] * 12, car_solo=[12.0] * 12)
    v = validate_features(feats)
    gaps = v[(v["category"] == "DATA_GAP_LEGAL") & (v["metric"] == "ldr")]
    assert gaps.empty, "công ty tài chính không bị đòi LDR"


def test_reported_out_of_range_ratio_is_still_flagged():
    """Số ĐƠN VỊ BÁO CÁO ngoài khoảng hợp lý vẫn phải gắn cờ cho KTV (vd LDR của SCB)."""
    feats = _features(ldr=[1995.65] * 2)
    v = validate_features(feats)
    assert (v["category"] == "OUT_OF_RANGE").any()


def test_dropped_ratio_is_reported_not_silent():
    """Ô bị bỏ phải nói rõ lý do — 'không có cờ' không được hiểu là 'an toàn'."""
    feats = _features(ldr=[float("nan")])
    feats.attrs["derived_ratio_gaps"] = pd.DataFrame(
        [{"bank_id": "CTTC_MIRAE_ASSET", "period": "2023-11", "metric": "ldr",
          "reason": "DENOMINATOR_COLLAPSED", "message": "tiền gửi ~ 0"}],
        columns=GAP_COLUMNS)
    v = validate_features(feats)
    note = v[v["category"] == "RATIO_NOT_EVALUATED"]
    assert len(note) == 1
    assert note["metric"].iloc[0] == "ldr"
    assert note["severity"].iloc[0] == "INFO"


def test_build_features_keeps_gaps_reachable_by_validation():
    """attrs phải sống sót qua add_trend/add_systemic/merge của build_features."""
    n = 8
    wide = pd.DataFrame({
        "bank_id": ["CTTC_X"] * n, "bank_name": ["X"] * n,
        "period": [f"2023-{m:02d}" for m in range(1, n + 1)],
        "period_ts": pd.date_range("2023-01-31", periods=n, freq="ME"),
        "customer_loans": [9994.57] * n, "deposits": [0.01] * n,
    })
    feats = build_features(wide, "monthly")
    assert not feats.attrs["derived_ratio_gaps"].empty
    assert feats["ldr"].isna().all()


def test_derive_ratios_always_publishes_a_gap_table():
    """Không có ô nào bị bỏ thì vẫn phải có bảng rỗng đúng schema."""
    out = derive_ratios(pd.DataFrame({
        "bank_id": ["A"], "bank_name": ["A"], "period": ["2023Q1"],
        "period_ts": pd.to_datetime(["2023-03-31"]),
        "customer_loans": [700.0], "deposits": [800.0],
    }))
    gaps = out.attrs["derived_ratio_gaps"]
    assert gaps.empty
    assert list(gaps.columns) == GAP_COLUMNS
