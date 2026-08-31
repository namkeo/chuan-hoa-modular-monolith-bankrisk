"""Tests for feature engineering: ratio derivation, trend & systemic features."""
from __future__ import annotations

import numpy as np

from src.feature_engineering import (add_systemic_features, add_trend_features,
                                     build_features, compute_systemic_stress,
                                     derive_ratios)


def test_derive_ratios_fills_from_components():
    import pandas as pd
    df = pd.DataFrame({
        "bank_id": ["A"], "bank_name": ["A"], "period": ["2023Q1"],
        "period_ts": pd.to_datetime(["2023-03-31"]),
        "total_assets": [1000.0], "equity": [100.0],
        "customer_loans": [700.0], "deposits": [800.0],
    })
    out = derive_ratios(df)
    assert abs(out["equity_to_assets"].iloc[0] - 10.0) < 1e-6
    assert abs(out["ldr"].iloc[0] - 87.5) < 1e-6


def _one_row(**metrics):
    import pandas as pd
    return pd.DataFrame({
        "bank_id": ["CTTC_X"], "bank_name": ["CTTC_X"], "period": ["2023-11"],
        "period_ts": pd.to_datetime(["2023-11-30"]), **{k: [v] for k, v in metrics.items()},
    })


def test_ldr_not_derived_when_deposits_absent():
    """Công ty tài chính không nhận tiền gửi -> KHÔNG có LDR, không phải LDR = ∞."""
    out = derive_ratios(_one_row(customer_loans=10092.83, deposits=0.0))
    assert out["ldr"].isna().all(), "tiền gửi = 0 không phải số chia hợp lệ"


def test_ldr_not_derived_from_rounding_dust():
    """Lỗi thật: CTTC Mirae Asset T11/2023 — tiền gửi 0,01 tỷ -> LDR 99.945.700%.

    Số dư 0,01 chỉ là phần làm tròn ở đơn vị "Tỷ đồng", không phải nguồn vốn. Chia
    cho nó ra con số vô nghĩa; chỉ tiêu phải bị coi là KHÔNG CÓ giá trị.
    """
    out = derive_ratios(_one_row(customer_loans=9994.57, deposits=0.01))
    assert out["ldr"].isna().all(), "LDR 99.945.700% phải bị loại, không được đánh giá"
    gaps = out.attrs["derived_ratio_gaps"]
    assert list(gaps["metric"]) == ["ldr"], "phải ghi nhận để KTV biết vì sao ô trống"
    assert gaps["reason"].iloc[0] == "DENOMINATOR_COLLAPSED"


def test_reported_ratio_is_never_overwritten():
    """LDR 1.995% của SCB là số ĐƠN VỊ BÁO CÁO — giữ nguyên cho KTV xem xét.

    derive_ratios chỉ điền vào ô trống; chặn giá trị bịa không được đụng vào số báo cáo
    (validation.py vẫn gắn cờ OUT_OF_RANGE cho nó).
    """
    out = derive_ratios(_one_row(customer_loans=386135.97, deposits=11137.71, ldr=1995.65))
    assert out["ldr"].iloc[0] == 1995.65


def test_negative_signals_are_kept():
    """Vốn/tài sản âm (GPBank), ROA âm sâu (SCB) là PHÁT HIỆN THẬT — không được chặn."""
    out = derive_ratios(_one_row(equity=-1400.0, total_assets=1000.0,
                                 profit_after_tax=-2470.0))
    assert out["equity_to_assets"].iloc[0] == -140.0
    assert out["roa"].iloc[0] == -247.0


def test_npl_ratio_zero_is_a_real_answer():
    """Nợ xấu = 0 nghĩa là tỷ lệ nợ xấu 0%, không phải thiếu dữ liệu."""
    out = derive_ratios(_one_row(npl_amount=0.0, customer_loans=500.0))
    assert out["npl_ratio"].iloc[0] == 0.0


def test_npl_ratio_above_loan_book_is_dropped():
    """Nợ xấu không thể vượt tổng dư nợ -> phép suy ra hỏng, không đánh giá."""
    out = derive_ratios(_one_row(npl_amount=7.7, customer_loans=1.63))
    assert out["npl_ratio"].isna().all()


def test_trend_features_present(synthetic_wide):
    out = add_trend_features(synthetic_wide, ["npl_ratio"], window=4)
    for suffix in ["__roll_mean", "__roll_std", "__roll_z", "__qoq", "__yoy", "__drawdown"]:
        assert f"npl_ratio{suffix}" in out.columns


def test_trend_features_survive_sparse_quarterly_reporting():
    """Chỉ tiêu báo cáo theo quý nằm trên lưới tháng: chỉ tháng cuối quý có số.

    pandas >= 3.0 bỏ fill_method='pad' của pct_change nên pct_change thô trả NaN
    khi kỳ liền trước trống -> qoq/yoy/accel từng thành 100% NaN. Phải lấy giá trị
    hợp lệ gần nhất trước khi tính biến động.
    """
    import pandas as pd
    n = 12
    vals = [np.nan] * n
    vals[2], vals[5], vals[8], vals[11] = 4.0, 5.0, 5.0, 6.0   # Mar/Jun/Sep/Dec
    df = pd.DataFrame({
        "bank_id": ["A"] * n, "bank_name": ["A"] * n,
        "period": [f"2023-{m:02d}" for m in range(1, n + 1)],
        "period_ts": pd.date_range("2023-01-31", periods=n, freq="ME"),
        "group2_ratio": vals,
    })
    out = add_trend_features(df, ["group2_ratio"], window=4)
    for suffix in ["__qoq", "__yoy", "__accel"]:
        col = out[f"group2_ratio{suffix}"]
        assert col.notna().any(), f"group2_ratio{suffix} không được toàn NaN"
    # Jun so với Mar: 4.0 -> 5.0 = +25%, ghi nhận tại kỳ báo cáo thật.
    assert abs(out["group2_ratio__qoq"].iloc[5] - 25.0) < 1e-6
    # Tháng chưa có số liệu mới thì giữ nguyên -> biến động 0 (bậc thang).
    assert abs(out["group2_ratio__qoq"].iloc[6] - 0.0) < 1e-6


def test_systemic_features_and_stress(synthetic_wide):
    out = add_systemic_features(synthetic_wide, ["npl_ratio"])
    assert "npl_ratio__pct_rank" in out.columns
    stress = compute_systemic_stress(synthetic_wide)
    assert not stress.empty
    assert "systemic_stress_index" in stress.columns


def test_build_features_pipeline(synthetic_wide):
    feats = build_features(synthetic_wide, "quarterly")
    assert not feats.empty
    assert feats.attrs.get("base_metrics")
    # high-risk-period flag column should exist once systemic stress is computed.
    assert "high_risk_period_flag" in feats.columns or "systemic_stress_pct" in feats.columns
