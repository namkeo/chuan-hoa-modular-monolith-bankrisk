"""Tests for risk scoring: weighted blend, rule floor and CRITICAL override."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.anomaly_detection import run_isolation_forest
from src.feature_engineering import build_features, compute_systemic_stress
from src.risk_scoring import (_level_from_score, compute_risk_scores,
                              bank_level_summary, domain_proxy_scores)
from src.rule_engine import evaluate_rules


def test_level_thresholds():
    assert _level_from_score(10) == "LOW"
    assert _level_from_score(40) == "MEDIUM"
    assert _level_from_score(70) == "HIGH"
    assert _level_from_score(95) == "CRITICAL"


def _score(synthetic_wide):
    feats = build_features(synthetic_wide, "quarterly")
    rf = evaluate_rules(feats)
    an = run_isolation_forest(feats, feats.attrs["base_metrics"])
    ss = compute_systemic_stress(feats)
    return feats, compute_risk_scores(feats, rf, an.table, None, None, ss)


def test_mandatory_critical_overrides_ml(synthetic_wide):
    feats, scores = _score(synthetic_wide)
    d = scores[scores["bank_id"] == "BANK_D"]
    assert not d.empty
    # BANK_D breaches mandatory legal limits -> forced CRITICAL, score >= 90.
    assert (d["risk_level"] == "CRITICAL").all()
    assert (d["final_risk_score"] >= 90).all()


def test_floor_is_lower_bound(synthetic_wide):
    _, scores = _score(synthetic_wide)
    # final_risk_score never drops below the rule-based floor.
    assert (scores["final_risk_score"] >= scores["rule_based_floor"] - 1e-6).all()


def test_healthy_bank_not_critical(synthetic_wide):
    _, scores = _score(synthetic_wide)
    a = scores[scores["bank_id"] == "BANK_A"]
    assert (a["risk_level"] != "CRITICAL").all()


def test_bank_ranking_sorted(synthetic_wide):
    _, scores = _score(synthetic_wide)
    ranking = bank_level_summary(scores)
    assert list(ranking["final_risk_score"]) == sorted(
        ranking["final_risk_score"], reverse=True)
    # Highest-risk bank should be BANK_D.
    assert ranking.iloc[0]["bank_id"] == "BANK_D"


# --------------------------------------------------------------------------- #
# Domain proxy scores: chỉ đánh giá đơn vị CÓ dữ liệu ở kỳ đó.
# --------------------------------------------------------------------------- #
def _domain_row(**metrics):
    base = {"bank_id": ["X"], "period": ["2025-12"]}
    return pd.DataFrame({**base, **{k: [v] for k, v in metrics.items()}})


def test_no_data_domain_is_not_evaluated():
    """Đơn vị không có chỉ tiêu nào của lĩnh vực -> điểm NaN, KHÔNG phải 0.

    Điểm 0 = 'đã đánh giá, rủi ro thấp nhất'. Gán 0 cho đơn vị thiếu dữ liệu (vd
    TCTCVM không có chỉ tiêu thanh khoản) sẽ khiến nó xếp như an toàn nhất.
    """
    out = domain_proxy_scores(_domain_row(car_solo=12.0), pd.DataFrame())
    assert pd.isna(out["credit_risk_score"].iloc[0])
    assert pd.isna(out["liquidity_risk_score"].iloc[0])


def test_reported_zero_risk_is_still_evaluated():
    """Nợ xấu 0 là 'đã đánh giá, rủi ro thấp' -> điểm 0 THẬT, không phải NaN."""
    out = domain_proxy_scores(_domain_row(npl_ratio=0.0), pd.DataFrame())
    assert out["credit_risk_score"].iloc[0] == 0.0


def test_high_metric_scores_high():
    out = domain_proxy_scores(_domain_row(npl_ratio=8.0), pd.DataFrame())
    assert out["credit_risk_score"].iloc[0] == 100.0


def test_failure_not_diluted_by_unevaluated_domains():
    """Điểm 'đổ vỡ' không được trộn điểm tín dụng/thanh khoản khi chúng chưa đánh giá.

    Đơn vị chỉ có vốn (car_solo) mà không có tín dụng/thanh khoản: failure phải bằng
    đúng tín hiệu vốn, không bị hai số 0 giả kéo xuống.
    """
    out = domain_proxy_scores(_domain_row(car_solo=5.0), pd.DataFrame())
    # (10 - 5) / 10 * 100 = 50, và không có thành phần nào khác -> 50 (không phải ~16).
    assert out["failure_risk_proxy_score"].iloc[0] == 50.0
    assert pd.isna(out["credit_risk_score"].iloc[0])


def test_domain_means_skip_unevaluated():
    """KPI trung bình (nanmean) bỏ qua đơn vị không đánh giá, không bị kéo tụt về 0."""
    df = pd.concat([_domain_row(npl_ratio=10.0).assign(bank_id="HIGH"),
                    _domain_row(car_solo=12.0).assign(bank_id="NODATA")],
                   ignore_index=True)
    out = domain_proxy_scores(df, pd.DataFrame())
    # HIGH=100, NODATA=NaN -> trung bình bỏ NaN = 100, không phải 50.
    assert out["credit_risk_score"].mean() == 100.0
