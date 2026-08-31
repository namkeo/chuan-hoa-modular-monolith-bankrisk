"""Tests for the expert rule engine: operators, violations, DATA_GAP, ngưỡng QĐ 682."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.rule_engine import (_evaluate, _tier_for, evaluate_rules,
                             load_institution_types, summarize_by_bank_period)

# Các ngân hàng tổng hợp trong fixture không có trong config thật -> cấp phân loại
# riêng cho test, nếu không mọi rule ngưỡng theo loại hình sẽ bị bỏ qua.
INST_CFG = {
    "banks": {b: {"type": "nhtm_co_phan"} for b in ["BANK_A", "BANK_B", "BANK_C", "BANK_D", "A"]},
    "special_control": [],
}


def test_operators():
    assert _evaluate("<", 7.0, 8.0) is True
    assert _evaluate("<", 9.0, 8.0) is False
    assert _evaluate(">", 90.0, 85.0) is True
    assert _evaluate("between", 82.0, [80.0, 85.0]) is True
    assert _evaluate("outside_range", 25.0, [-20.0, 20.0]) is True
    assert _evaluate("missing", None, None) is True
    assert _evaluate("<", None, 8.0) is False  # missing value, non-missing op


def test_evaluate_rules_flags_breaches(synthetic_wide):
    findings = evaluate_rules(synthetic_wide, inst_cfg=INST_CFG)
    assert not findings.empty
    # BANK_D breaches CAR < Ngưỡng 3 (8%) -> CRITICAL violation present.
    d_car = findings[(findings["bank_id"] == "BANK_D") &
                     (findings["metric"] == "car_solo") &
                     (findings["severity"] == "CRITICAL")]
    assert not d_car.empty
    # Healthy BANK_A has no CRITICAL legal violation.
    a_crit = findings[(findings["bank_id"] == "BANK_A") &
                      (findings["severity"] == "CRITICAL") &
                      (findings["finding_type"] == "VIOLATION")]
    assert a_crit.empty


def test_data_gap_for_missing_legal_metric():
    # A wide table missing a legally-critical metric (e.g. car_solo) entirely.
    df = pd.DataFrame({
        "bank_id": ["A", "A"], "bank_name": ["A", "A"],
        "period": ["2023Q1", "2023Q2"],
        "period_ts": pd.to_datetime(["2023-03-31", "2023-06-30"]),
        "npl_ratio": [2.0, 2.5],
    })
    findings = evaluate_rules(df, inst_cfg=INST_CFG)
    # CAR rule cannot be checked -> DATA_GAP entry exists.
    assert (findings["finding_type"] == "DATA_GAP").any()


def test_summary_worst_severity(synthetic_wide):
    findings = evaluate_rules(synthetic_wide, inst_cfg=INST_CFG)
    summ = summarize_by_bank_period(findings)
    d = summ[summ["bank_id"] == "BANK_D"]
    assert not d.empty
    assert (d["n_critical"] > 0).any()


# --------------------------------------------------------------------------- #
# Ngưỡng giám sát 3 bậc theo loại hình (QĐ 682 / QĐ 618)
# --------------------------------------------------------------------------- #
def test_tier_bands_are_exclusive_lower_riskier():
    """CAR (càng nhỏ càng rủi ro), NHTM cổ phần: N1=9.5, N2=8.5, N3=8.0."""
    tiers = {"n1": 9.5, "n2": 8.5, "n3": 8.0}
    assert _tier_for(10.0, tiers, "lower_riskier") is None   # >= N1: bình thường
    assert _tier_for(9.0, tiers, "lower_riskier") == "n1"    # N2 <= x < N1
    assert _tier_for(8.2, tiers, "lower_riskier") == "n2"    # N3 <= x < N2
    assert _tier_for(7.5, tiers, "lower_riskier") == "n3"    # x < N3: vi phạm


def test_tier_bands_are_exclusive_higher_riskier():
    """LDR (càng lớn càng rủi ro), NHTM cổ phần: N1=80, N2=83, N3=85."""
    tiers = {"n1": 80.0, "n2": 83.0, "n3": 85.0}
    assert _tier_for(75.0, tiers, "higher_riskier") is None
    assert _tier_for(81.0, tiers, "higher_riskier") == "n1"
    assert _tier_for(84.0, tiers, "higher_riskier") == "n2"
    assert _tier_for(90.0, tiers, "higher_riskier") == "n3"


def _one_row(bank_id: str, **metrics) -> pd.DataFrame:
    return pd.DataFrame([{
        "bank_id": bank_id, "bank_name": bank_id, "period": "2024-01",
        "period_ts": pd.Timestamp("2024-01-31"), **metrics}])


def test_threshold_depends_on_institution_type():
    """CAR 8.5%: hợp lệ với ngân hàng (N3=8) nhưng VI PHẠM với công ty tài chính (N3=9)."""
    cfg = {"banks": {"NH": {"type": "nhtm_co_phan"}, "CTTC": {"type": "cong_ty_tai_chinh"}},
           "special_control": []}
    df = pd.concat([_one_row("NH", car_solo=8.5), _one_row("CTTC", car_solo=8.5)])
    f = evaluate_rules(df, inst_cfg=cfg)
    car = f[f["rule_id"] == "QD682_CAR_SOLO"]
    nh = car[car["bank_id"] == "NH"]
    cttc = car[car["bank_id"] == "CTTC"]
    assert (nh["finding_type"] == "VIOLATION").sum() == 0
    assert (cttc["finding_type"] == "VIOLATION").sum() == 1


def test_ldr_not_applied_to_finance_companies():
    """QĐ 682 để trống ô LDR của công ty tài chính -> không được sinh vi phạm LDR."""
    cfg = {"banks": {"NH": {"type": "nhtm_co_phan"}, "CTTC": {"type": "cong_ty_tai_chinh"}},
           "special_control": []}
    df = pd.concat([_one_row("NH", ldr=95.0), _one_row("CTTC", ldr=95.0)])
    f = evaluate_rules(df, inst_cfg=cfg)
    ldr = f[(f["rule_id"] == "QD682_LDR") & (f["finding_type"] == "VIOLATION")]
    assert set(ldr["bank_id"]) == {"NH"}, "LDR không áp cho công ty tài chính"


def test_special_control_bank_gets_no_threshold_violation():
    """QĐ 682 Phụ lục 3 mục 3.2: đơn vị kiểm soát đặc biệt không so ngưỡng."""
    cfg = {"banks": {"KSDB": {"type": "nhtm_co_phan"}},
           "special_control": [{"bank_id": "KSDB", "reason": "kiểm soát đặc biệt"}]}
    f = evaluate_rules(_one_row("KSDB", car_solo=3.0, ldr=99.0), inst_cfg=cfg)
    # CAR 3% và LDR 99% vượt xa Ngưỡng 3, nhưng KSĐB thì không so ngưỡng ->
    # không được có finding ngưỡng nào GẮN VỚI đơn vị này.
    tiered = f[f["rule_id"].str.startswith("QD68", na=False)
               & (f["bank_id"] == "KSDB")]
    assert tiered.empty, "không được so ngưỡng với đơn vị kiểm soát đặc biệt"
    # ...nhưng phải nói rõ lý do, không im lặng.
    assert (f["finding_type"] == "SPECIAL_CONTROL").any()


def test_unclassified_bank_is_reported_not_silently_skipped():
    """Đơn vị chưa khai loại hình phải sinh DATA_GAP, không được bỏ qua im lặng."""
    cfg = {"banks": {}, "special_control": []}
    f = evaluate_rules(_one_row("NEW_BANK", car_solo=3.0), inst_cfg=cfg)
    unknown = f[f["rule_id"] == "INSTITUTION_TYPE_UNKNOWN"]
    assert not unknown.empty
    assert (unknown["finding_type"] == "DATA_GAP").all()


def test_real_config_covers_every_bank_in_rules():
    """Mọi loại hình dùng trong institution_types.yaml phải có nhãn khai báo."""
    cfg_types, excluded = load_institution_types()
    labels = set((__import__("src.utils", fromlist=["load_config"])
                  .load_config("institution_types").get("type_labels") or {}))
    used = {t for t in cfg_types.values() if t}
    assert used <= labels, f"loại hình thiếu nhãn: {used - labels}"
    assert not (set(cfg_types) & set(excluded)), "đơn vị vừa phân loại vừa KSĐB"
