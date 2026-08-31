"""Composite risk scoring per bank-period.

Blends the expert rule-based system, Isolation Forest anomaly score, K-means
cluster risk, time-series trend risk, data-quality risk and systemic-period risk
into a single ``final_risk_score`` in [0, 100] and a ``risk_level`` in
{LOW, MEDIUM, HIGH, CRITICAL}.

Hard guarantees (audit requirement):
  * ``final_risk_score = max(rule_based_floor, weighted_score)`` — the ML blend can
    only *raise* the score above the floor a violated legal rule imposes, never
    lower it.
  * If any *mandatory legal* rule (severity CRITICAL, status ACTIVE) is violated,
    ``risk_level`` is forced to CRITICAL regardless of the ML score.

The module also derives domain proxy scores (credit / liquidity / fraud / failure).
None of these are predictions of certain fraud or failure — they are early-warning
*risk rankings* built from anomaly, trend, rule and cluster signals, as required by
the unsupervised nature of the problem.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import DATA_ROOT, LOG, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]

SEVERITY_ORDER = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
LEVEL_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _norm_0_100(s: pd.Series) -> pd.Series:
    """Min-max scale a series into 0..100 (constant series -> 0)."""
    s = pd.to_numeric(s, errors="coerce")
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return pd.Series(0.0, index=s.index)
    return (s - lo) / (hi - lo) * 100


def _mandatory_critical_rule_ids(rules_cfg: dict) -> set[str]:
    """Rule ids that, when violated, must force CRITICAL (legal + ACTIVE)."""
    out = set()
    for r in rules_cfg.get("rules", []):
        if r.get("severity") == "CRITICAL" and r.get("status", "ACTIVE") == "ACTIVE":
            out.add(r["rule_id"])
    return out


# --------------------------------------------------------------------------- #
# Component scores
# --------------------------------------------------------------------------- #
def rule_violation_score(rule_findings: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Per bank-period rule score = max severity points over its findings (0..100),
    plus per-domain max severity points and the worst severity / flags."""
    sev_pts = cfg.get("risk_scoring", {}).get("severity_points", {})
    cols = ["bank_id", "period", "rule_violation_score", "worst_rule_severity",
            "has_mandatory_critical", "n_critical", "n_high", "n_data_gap",
            "credit_rule_pts", "liquidity_rule_pts", "capital_rule_pts"]
    if rule_findings is None or rule_findings.empty:
        return pd.DataFrame(columns=cols)

    rules_cfg = load_config("regulatory_rules")
    mandatory = _mandatory_critical_rule_ids(rules_cfg)

    rows = []
    for (bid, period), sub in rule_findings.groupby(["bank_id", "period"]):
        if bid is None:
            continue
        pts = sub["severity"].map(lambda s: sev_pts.get(s, 0))
        sev_present = [s for s in SEVERITY_ORDER if (sub["severity"] == s).any()]
        worst = sev_present[-1] if sev_present else (
            "DATA_GAP" if (sub["severity"] == "DATA_GAP").any() else "INFO")
        has_mand = bool(sub.loc[sub["finding_type"] == "VIOLATION", "rule_id"]
                        .isin(mandatory).any())

        def dom_pts(domain):
            d = sub[sub["risk_domain"] == domain]
            return float(d["severity"].map(lambda s: sev_pts.get(s, 0)).max()) if not d.empty else 0.0

        rows.append({
            "bank_id": bid, "period": period,
            "rule_violation_score": float(pts.max()) if len(pts) else 0.0,
            "worst_rule_severity": worst,
            "has_mandatory_critical": has_mand,
            "n_critical": int((sub["severity"] == "CRITICAL").sum()),
            "n_high": int((sub["severity"] == "HIGH").sum()),
            "n_data_gap": int((sub["severity"] == "DATA_GAP").sum()),
            "credit_rule_pts": dom_pts("credit"),
            "liquidity_rule_pts": dom_pts("liquidity"),
            "capital_rule_pts": dom_pts("capital"),
        })
    return pd.DataFrame(rows, columns=cols)


def trend_risk_score(features: pd.DataFrame) -> pd.DataFrame:
    """Per bank-period trend risk from oriented rolling z-scores of stress metrics.

    Higher = worsening fast. Uses the ``*__roll_z`` columns produced by
    feature_engineering; metrics are oriented so an adverse move is positive.
    """
    # sign: +1 means a higher value is worse.
    oriented = {
        "npl_ratio": +1, "group2_ratio": +1, "ldr": +1, "st_funding_for_mlt_loans": +1,
        "cir": +1, "credit_growth_yoy": +1,
        "car_solo": -1, "car_consolidated": -1, "roa": -1, "roe": -1,
        "liquidity_reserve_ratio": -1, "llr_coverage": -1, "solvency_30d_vnd": -1,
    }
    rows = []
    for _, row in features.iterrows():
        comps = []
        for m, sign in oriented.items():
            z = row.get(f"{m}__roll_z")
            if pd.notna(z):
                comps.append(sign * float(z))
        # Positive oriented z = adverse; clip to [0, 3] then scale to 0..100.
        adverse = [max(0.0, c) for c in comps]
        score = float(np.clip(np.mean(adverse), 0, 3) / 3 * 100) if adverse else 0.0
        rows.append({"bank_id": row["bank_id"], "period": row["period"],
                     "trend_risk_score": round(score, 2)})
    return pd.DataFrame(rows)


def _blend_domain(signals: list[float], rule_pts: float) -> float:
    """Điểm lĩnh vực 0..100 — hoặc NaN nếu KHÔNG có dữ liệu để đánh giá.

    Không có tín hiệu nào VÀ không có áp lực rule => đơn vị không có chỉ tiêu nào của
    lĩnh vực này ở kỳ này => trả NaN ("không đánh giá"), KHÔNG trả 0. Điểm 0 nghĩa là
    "đã đánh giá và rủi ro thấp nhất" — gán 0 cho đơn vị thiếu dữ liệu sẽ khiến nó
    xếp như đơn vị an toàn nhất và kéo tụt điểm trung bình toàn hệ thống.
    """
    if signals:
        return float(max(float(np.nanmean(signals)), rule_pts))
    if rule_pts > 0:            # rule chỉ kích hoạt khi có giá trị -> coi như có dữ liệu
        return float(rule_pts)
    return np.nan


def _round2(x: float) -> float:
    return round(float(x), 2) if x == x else np.nan   # x == x là False khi NaN


# --------------------------------------------------------------------------- #
# Gom cụm cờ đỏ theo bản chất (readme_explain_bo_sung.docx §13.4.1 + §13.6):
# các cờ cùng phản ánh một bản chất chỉ được đếm MỘT lần khi tính điểm, để "ưu
# tiên số lượng, mức độ và độ bền của các phân kỳ" thay vì cộng dồn tỷ lệ xấu.
# --------------------------------------------------------------------------- #
CREDIT_FLAG_CLUSTERS = {
    "growth_capital": {"CREDIT_GROWTH_CAPITAL_GAP", "CREDIT_GROWTH_RWA_DIVERGENCE",
                       "HOT_CREDIT_WEAK_SUPPORT"},
    "migration_provision": {"NPL_GROUP2_MIGRATION", "PROVISION_LAG", "NPL_DROP_DIVERGENCE"},
    "concentration": {"CONCENTRATION_BUILDUP"},
    "accrued_offbalance": {"ACCRUED_INTEREST_CREDIT_STRESS"},
}
LIQUIDITY_FLAG_CLUSTERS = {
    "buffer_30d": {"HQLA_OUTFLOW_STRESS"},
    "funding_stability": {"DEPOSIT_CASA_STRESS", "WHOLESALE_FUNDING_SUBSTITUTION",
                          "LDR_HIGH_DEPOSIT_STRESS"},
    "maturity_mismatch": {"MATURITY_MISMATCH_BUILDUP"},
    "market_sensitivity": {"FX_LIQUIDITY_DIVERGENCE", "INTEREST_RATE_GAP_LIQUIDITY"},
}
FRAUD_FLAG_CLUSTERS = {
    "earnings_quality": {"ACCRUED_INTEREST_PROFIT_DIVERGENCE", "PROFIT_UP_OPS_DOWN"},
    "classification_provision": {"NPL_GROUP2_PROVISION_DIVERGENCE", "NPL_DROP_DIVERGENCE",
                                 "OFFBALANCE_RISK_SHIFT"},
    "window_dressing": {"YEAR_END_LIQUIDITY_WINDOW_DRESSING", "FUNDING_SOURCE_SWAP"},
    "capital_rwa": {"CAPITAL_COMPONENT_MISMATCH", "CREDIT_GROWTH_RWA_DIVERGENCE"},
}


def _flag_lookup(validation_findings: pd.DataFrame | None) -> dict:
    """(bank_id, period) -> set các category cờ đỏ đã kích hoạt."""
    out: dict = {}
    if validation_findings is None or validation_findings.empty:
        return out
    v = validation_findings.dropna(subset=["bank_id", "period"])
    for (bid, period), sub in v.groupby(["bank_id", "period"]):
        out[(bid, period)] = set(sub["category"].astype(str))
    return out


def _clusters_triggered(cats: set, clusters: dict) -> list[str]:
    return [name for name, members in clusters.items() if cats & members]


def domain_proxy_scores(features: pd.DataFrame, rule_score: pd.DataFrame,
                        validation_findings: pd.DataFrame | None = None) -> pd.DataFrame:
    """Credit / liquidity / fraud / failure proxy scores per bank-period.

    These are *risk rankings*, not certainty predictions. Each blends the relevant
    rule pressure with adverse level/trend signals available in the features.

    Đơn vị KHÔNG có dữ liệu của một lĩnh vực ở một kỳ -> điểm lĩnh vực đó là NaN
    ("không đánh giá") thay vì 0. Nhờ đó bảng xếp hạng, KPI trung bình (nanmean bỏ
    NaN) và điểm "đổ vỡ" (không trộn điểm lĩnh vực chưa đánh giá) đều không tính oan
    đơn vị thiếu dữ liệu là "an toàn".

    Mở rộng theo readme_explain_bo_sung.docx §13.2/13.3/13.6: giữ các biến lõi;
    mỗi NHÓM chỉ tiêu bổ sung tạo đúng MỘT điểm đại diện (tránh đếm trùng); chỉ
    tiêu chưa có ngưỡng pháp lý dùng bách phân vị hệ thống (``__pct_rank``) thay
    vì tự gán ngưỡng; các cờ đỏ được gom cụm theo bản chất trước khi tính điểm.
    """
    f = features.set_index(["bank_id", "period"])
    rs = rule_score.set_index(["bank_id", "period"]) if not rule_score.empty else None
    flags = _flag_lookup(validation_findings)
    rows = []
    for (bid, period), row in f.iterrows():
        def g(col):
            v = row.get(col)
            return float(v) if pd.notna(v) else np.nan

        def pct(col):
            """Bách phân vị hệ thống 0..100 của chỉ tiêu (cao = rủi ro cao)."""
            return g(f"{col}__pct_rank")

        def rule_pts(col):
            if rs is None or (bid, period) not in rs.index:
                return 0.0
            v = rs.loc[(bid, period), col]
            return float(v) if pd.notna(v) else 0.0

        cats = flags.get((bid, period), set())

        # ---- Credit risk: biến lõi — NPL, group2, low coverage, hot growth ----
        credit_signals = []
        if not np.isnan(g("npl_ratio")):
            credit_signals.append(np.clip(g("npl_ratio") / 5 * 100, 0, 100))
        if not np.isnan(g("group2_ratio")):
            credit_signals.append(np.clip(g("group2_ratio") / 5 * 100, 0, 100))
        if not np.isnan(g("llr_coverage")):
            credit_signals.append(np.clip((100 - g("llr_coverage")) / 100 * 100, 0, 100))
        if not np.isnan(g("credit_growth_yoy")):
            credit_signals.append(np.clip(g("credit_growth_yoy") / 40 * 100, 0, 100))

        # ---- Điểm nhóm bổ sung tín dụng (§13.2) — 1 điểm đại diện / nhóm ----
        # Nhóm 1: cơ cấu kỳ hạn danh mục (không có ngưỡng pháp lý -> bách phân vị).
        credit_structure = float(np.nanmean([pct("mlt_loan_ratio")])) \
            if not np.isnan(pct("mlt_loan_ratio")) else np.nan
        # Nhóm 3: dự phòng & chi phí rủi ro — đệm mỏng (đảo chiều) + chi phí cao.
        prov_parts = []
        if not np.isnan(pct("provision_to_loans")):
            prov_parts.append(100 - pct("provision_to_loans"))
        if not np.isnan(pct("credit_cost_ratio")):
            prov_parts.append(pct("credit_cost_ratio"))
        credit_provision = float(np.nanmean(prov_parts)) if prov_parts else np.nan
        # Nhóm 4: tập trung tín dụng — lĩnh vực rủi ro/BĐS/không TSBĐ/khách hàng lớn.
        conc_parts = [pct(c) for c in ("risky_sector_ratio", "real_estate_loan_ratio",
                                       "unsecured_loan_ratio", "large_borrower_ratio",
                                       "largest_customer_group_ratio")]
        conc_parts = [p for p in conc_parts if not np.isnan(p)]
        credit_concentration = float(np.nanmean(conc_parts)) if conc_parts else np.nan
        # Nhóm 5: lãi dự thu & cam kết ngoại bảng.
        offb_parts = [p for p in (pct("accrued_interest_to_loans"),
                                  pct("offbalance_to_assets")) if not np.isnan(p)]
        if not np.isnan(g("bad_offbalance_ratio")):
            offb_parts.append(float(np.clip(g("bad_offbalance_ratio") / 5 * 100, 0, 100)))
        credit_offbalance = float(np.nanmean(offb_parts)) if offb_parts else np.nan
        # Nhóm 6: sức chịu đựng vốn — CAR sát sàn pháp lý 8%, đòn bẩy cao.
        cap_parts = []
        if not np.isnan(g("car_solo")):
            cap_parts.append(float(np.clip((11 - g("car_solo")) / 3 * 100, 0, 100)))
        if not np.isnan(g("equity_to_assets")):
            cap_parts.append(float(np.clip((8 - g("equity_to_assets")) / 8 * 100, 0, 100)))
        credit_capital = float(np.nanmean(cap_parts)) if cap_parts else np.nan

        for grp_score in (credit_structure, credit_provision, credit_concentration,
                          credit_offbalance):
            if not np.isnan(grp_score):
                credit_signals.append(grp_score)
        # Nhóm 6 (vốn/RWA) là biến HỖ TRỢ (§13.1): chỉ bổ trợ khi lĩnh vực tín dụng
        # đã được đánh giá bằng dữ liệu danh mục — đơn vị chỉ có số liệu vốn
        # KHÔNG được coi là "đã đánh giá tín dụng" (giữ nguyên tắc NaN-khi-thiếu).
        if credit_signals and not np.isnan(credit_capital):
            credit_signals.append(credit_capital)
        # Cờ đỏ tín dụng đã gom cụm: mỗi cụm kích hoạt +25 điểm tín hiệu.
        credit_clusters = _clusters_triggered(cats, CREDIT_FLAG_CLUSTERS)
        if credit_clusters:
            credit_signals.append(float(np.clip(len(credit_clusters) * 25, 0, 100)))
        credit = _blend_domain(credit_signals, rule_pts("credit_rule_pts"))

        # ---- Liquidity risk: biến lõi — LDR, ST funding for MLT, reserve/solvency ----
        liq_signals = []
        if not np.isnan(g("ldr")):
            liq_signals.append(np.clip((g("ldr") - 70) / 30 * 100, 0, 100))
        if not np.isnan(g("st_funding_for_mlt_loans")):
            liq_signals.append(np.clip(g("st_funding_for_mlt_loans") / 34 * 100, 0, 100))
        if not np.isnan(g("liquidity_reserve_ratio")):
            liq_signals.append(np.clip((20 - g("liquidity_reserve_ratio")) / 20 * 100, 0, 100))
        if not np.isnan(g("avg_liquid_asset_ratio")):
            # Analytical reference ~15% liquid assets / total assets (REVIEW_REQUIRED).
            liq_signals.append(np.clip((15 - g("avg_liquid_asset_ratio")) / 15 * 100, 0, 100))
        if not np.isnan(g("solvency_30d_vnd")):
            liq_signals.append(np.clip((50 - g("solvency_30d_vnd")) / 50 * 100, 0, 100))

        # ---- Điểm nhóm bổ sung thanh khoản (§13.3) — 1 điểm đại diện / nhóm ----
        # Nhóm 2: ổn định tiền gửi/CASA — CASA thấp (đảo chiều) + tiền gửi co hẹp.
        dep_parts = []
        if not np.isnan(pct("casa")):
            dep_parts.append(100 - pct("casa"))
        dep_qoq = g("deposits__qoq")
        if not np.isnan(dep_qoq) and dep_qoq < 0:
            dep_parts.append(float(np.clip(-dep_qoq * 5, 0, 100)))
        liq_deposit = float(np.nanmean(dep_parts)) if dep_parts else np.nan
        # Nhóm 2b: phụ thuộc vốn bán buôn.
        liq_wholesale = pct("wholesale_funding_share")
        # Nhóm 4: tài sản dễ chuyển đổi so với tiền gửi (đệm thứ cấp mỏng = rủi ro).
        liq_secondary = (100 - pct("liquid_assets_to_deposits")
                         if not np.isnan(pct("liquid_assets_to_deposits")) else np.nan)
        # Nhóm 5: nhạy cảm thị trường — lệch tái định giá, trạng thái ngoại tệ,
        # khả năng chi trả ngoại tệ (ngưỡng QĐ682 ngoại tệ 10%).
        mkt_parts = []
        if not np.isnan(g("rate_sensitive_gap_ratio")):
            mkt_parts.append(float(np.clip(abs(g("rate_sensitive_gap_ratio")) / 50 * 100, 0, 100)))
        if not np.isnan(g("fx_position_ratio")):
            mkt_parts.append(float(np.clip(abs(g("fx_position_ratio")) / 20 * 100, 0, 100)))
        if not np.isnan(g("solvency_30d_fx")):
            mkt_parts.append(float(np.clip((10 - g("solvency_30d_fx")) / 10 * 100, 0, 100)))
        liq_market = float(np.nanmean(mkt_parts)) if mkt_parts else np.nan

        for grp_score in (liq_deposit, liq_wholesale, liq_secondary):
            if not np.isnan(grp_score):
                liq_signals.append(grp_score)
        # Nhóm 5 (nhạy cảm thị trường) là biến HỖ TRỢ (§13.1): chỉ bổ trợ khi đã có
        # tín hiệu thanh khoản thực — không tự mình kết luận "đã đánh giá thanh khoản".
        if liq_signals and not np.isnan(liq_market):
            liq_signals.append(liq_market)
        liq_clusters = _clusters_triggered(cats, LIQUIDITY_FLAG_CLUSTERS)
        if liq_clusters:
            liq_signals.append(float(np.clip(len(liq_clusters) * 25, 0, 100)))
        liquidity = _blend_domain(liq_signals, rule_pts("liquidity_rule_pts"))

        # ---- Fraud proxy: divergence / masking red-flag style signals ----
        # NPL falling while group2 rising, profit jump vs flat income, accrued
        # interest stretch. Uses available trend cols when present.
        # "Đánh giá được" khi có ÍT NHẤT một đầu vào; không có đầu vào nào -> NaN
        # (không đủ dữ liệu/lịch sử để soi dấu hiệu che giấu). Có đầu vào nhưng không
        # kích hoạt pattern nào -> 0 (đã đánh giá, không có cờ đỏ).
        fraud_inputs = [g("npl_ratio__roll_z"), g("group2_ratio__roll_z"),
                        g("profit_before_tax__qoq"), g("toi__qoq"),
                        g("accrued_interest_days")]
        fraud_evaluable = any(not np.isnan(x) for x in fraud_inputs) or bool(cats)
        fraud_signals = []
        npl_z = g("npl_ratio__roll_z")
        g2_z = g("group2_ratio__roll_z")
        if not np.isnan(npl_z) and not np.isnan(g2_z) and npl_z < -0.5 and g2_z > 0.5:
            fraud_signals.append(80.0)
        prof_qoq = g("profit_before_tax__qoq")
        toi_qoq = g("toi__qoq")
        if not np.isnan(prof_qoq) and not np.isnan(toi_qoq) and prof_qoq > 20 and toi_qoq < 0:
            fraud_signals.append(70.0)
        if not np.isnan(g("accrued_interest_days")):
            fraud_signals.append(np.clip((g("accrued_interest_days") - 60) / 120 * 100, 0, 100))
        # §13.6: điểm gian lận ưu tiên SỐ CỤM phân kỳ kích hoạt (không cộng dồn
        # từng cờ) — 4 cụm: chất lượng lợi nhuận, phân loại nợ/dự phòng, làm đẹp
        # số liệu cuối kỳ, vốn/RWA.
        fraud_clusters = _clusters_triggered(cats, FRAUD_FLAG_CLUSTERS)
        if fraud_clusters:
            fraud_signals.append(float(np.clip(len(fraud_clusters) * 30, 0, 100)))
        if not fraud_evaluable:
            fraud = np.nan
        else:
            fraud = float(np.nanmean(fraud_signals)) if fraud_signals else 0.0

        # ---- Failure proxy: thin capital + bad assets + weak liquidity + losses ----
        # Chỉ trộn điểm tín dụng/thanh khoản khi CHÚNG đã được đánh giá (không NaN) —
        # nếu không, một đơn vị thiếu dữ liệu sẽ được cộng thêm hai số 0 giả làm loãng.
        fail_signals = []
        if not np.isnan(g("car_solo")):
            fail_signals.append(np.clip((10 - g("car_solo")) / 10 * 100, 0, 100))
        if not np.isnan(g("equity_to_assets")):
            fail_signals.append(np.clip((8 - g("equity_to_assets")) / 8 * 100, 0, 100))
        if not np.isnan(g("roa")):
            fail_signals.append(np.clip((0.5 - g("roa")) / 1.0 * 100, 0, 100))
        if not np.isnan(credit):
            fail_signals.append(credit * 0.5)
        if not np.isnan(liquidity):
            fail_signals.append(liquidity * 0.5)
        failure = float(np.nanmean(fail_signals)) if fail_signals else np.nan

        rows.append({
            "bank_id": bid, "period": period,
            "credit_risk_score": _round2(credit),
            "liquidity_risk_score": _round2(liquidity),
            "fraud_risk_proxy_score": _round2(fraud),
            "failure_risk_proxy_score": _round2(failure),
            # Điểm nhóm bổ sung (§13.2/13.3) — phục vụ hiển thị/diễn giải kiểm toán.
            "credit_structure_score": _round2(credit_structure),
            "credit_provision_score": _round2(credit_provision),
            "credit_concentration_score": _round2(credit_concentration),
            "credit_offbalance_score": _round2(credit_offbalance),
            "credit_capital_score": _round2(credit_capital),
            "liq_deposit_score": _round2(liq_deposit),
            "liq_wholesale_score": _round2(liq_wholesale),
            "liq_secondary_score": _round2(liq_secondary),
            "liq_market_score": _round2(liq_market),
            # Số CỤM cờ đỏ kích hoạt + danh sách cờ (đã gom theo bản chất §13.6).
            "credit_flag_clusters": len(credit_clusters),
            "liq_flag_clusters": len(liq_clusters),
            "fraud_flag_clusters": len(fraud_clusters),
            "fraud_flags": ", ".join(sorted(cats & set().union(*FRAUD_FLAG_CLUSTERS.values()))),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def compute_risk_scores(
    features: pd.DataFrame,
    rule_findings: pd.DataFrame,
    anomaly_table: pd.DataFrame,
    cluster_table: pd.DataFrame | None = None,
    validation_findings: pd.DataFrame | None = None,
    systemic_stress: pd.DataFrame | None = None,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """Produce the master per bank-period risk table.

    Returns one row per bank-period with all component scores, ``final_risk_score``
    and ``risk_level`` (with the legal CRITICAL override applied).
    """
    if features is None or features.empty:
        return pd.DataFrame()
    cfg = cfg or load_config("model_config")
    weights = cfg.get("risk_scoring", {}).get("weights", {})
    floors = cfg.get("risk_scoring", {}).get("rule_floor", {})

    base = features[ID_COLS].copy()

    # --- rule component ---
    rscore = rule_violation_score(rule_findings, cfg)
    base = base.merge(rscore, on=["bank_id", "period"], how="left")

    # --- anomaly component ---
    if anomaly_table is not None and not anomaly_table.empty:
        a = anomaly_table[["bank_id", "period", "anomaly_score", "anomaly_label",
                           "top_features"]].copy()
        a = a.rename(columns={"anomaly_score": "anomaly_score_norm"})
        base = base.merge(a, on=["bank_id", "period"], how="left")
    else:
        base["anomaly_score_norm"] = np.nan
        base["anomaly_label"] = 0
        base["top_features"] = ""

    # --- trend component ---
    tscore = trend_risk_score(features)
    base = base.merge(tscore, on=["bank_id", "period"], how="left")

    # --- cluster component (cross-sectional, latest snapshot -> broadcast) ---
    if cluster_table is not None and not cluster_table.empty and "cluster_risk_score" in cluster_table.columns:
        c = cluster_table[["bank_id", "cluster_id", "cluster_risk_label",
                           "cluster_risk_score"]].drop_duplicates("bank_id")
        base = base.merge(c, on="bank_id", how="left")
    else:
        base["cluster_id"] = np.nan
        base["cluster_risk_label"] = None
        base["cluster_risk_score"] = np.nan

    # --- data-quality component (share of validation findings on this bank-period) ---
    base["data_quality_risk_score"] = _data_quality_score(base, validation_findings)

    # --- systemic-period component ---
    if systemic_stress is not None and not systemic_stress.empty:
        ss = systemic_stress[["period", "systemic_stress_pct"]].rename(
            columns={"systemic_stress_pct": "systemic_period_risk_score"})
        base = base.merge(ss, on="period", how="left")
    else:
        base["systemic_period_risk_score"] = np.nan

    # --- domain proxy scores (kèm cờ đỏ mở rộng từ validation — §13.4/13.6) ---
    proxies = domain_proxy_scores(features, rscore, validation_findings)
    base = base.merge(proxies, on=["bank_id", "period"], how="left")

    # Fill component NaNs with 0 for the weighted blend.
    comp_cols = ["rule_violation_score", "anomaly_score_norm", "trend_risk_score",
                 "cluster_risk_score", "data_quality_risk_score",
                 "systemic_period_risk_score"]
    for c in comp_cols:
        base[c] = pd.to_numeric(base.get(c), errors="coerce").fillna(0.0)

    # --- weighted blend ---
    base["weighted_score"] = sum(
        weights.get(c, 0.0) * base[c] for c in comp_cols).clip(0, 100)

    # --- rule floor ---
    base["rule_based_floor"] = base["worst_rule_severity"].map(
        lambda s: floors.get(s, 0) if isinstance(s, str) else 0).fillna(0.0)
    base["has_mandatory_critical"] = base["has_mandatory_critical"].fillna(False)

    base["final_risk_score"] = np.maximum(base["weighted_score"],
                                          base["rule_based_floor"]).round(2)

    # --- risk level with legal CRITICAL override ---
    base["risk_level"] = base["final_risk_score"].map(_level_from_score)
    base.loc[base["has_mandatory_critical"] == True, "risk_level"] = "CRITICAL"  # noqa: E712
    base.loc[base["has_mandatory_critical"] == True, "final_risk_score"] = \
        base.loc[base["has_mandatory_critical"] == True, "final_risk_score"].clip(lower=90)

    base["risk_rank"] = base["final_risk_score"].rank(ascending=False, method="min").astype(int)
    LOG.info("Risk scoring: %d bank-periods | CRITICAL=%d HIGH=%d",
             len(base), (base["risk_level"] == "CRITICAL").sum(),
             (base["risk_level"] == "HIGH").sum())
    return base


def _data_quality_score(base: pd.DataFrame, validation: pd.DataFrame | None) -> pd.Series:
    """Map validation findings onto a 0..100 data-quality risk per bank-period."""
    score = pd.Series(0.0, index=base.index)
    # DATA_GAP rule pressure already captured; add validation severity here.
    if validation is None or validation.empty:
        # Fall back on rule DATA_GAP count.
        if "n_data_gap" in base.columns:
            score = (pd.to_numeric(base["n_data_gap"], errors="coerce").fillna(0)
                     .clip(0, 5) / 5 * 100)
        return score
    sev_pts = {"INFO": 10, "LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 100,
               "DATA_GAP": 70, "CRITICAL_DATA_GAP": 100}
    v = validation.copy()
    v["pts"] = v["severity"].map(lambda s: sev_pts.get(s, 25))
    by_bp = v.groupby(["bank_id", "period"])["pts"].max()
    by_bank = v[v["period"].isna()].groupby("bank_id")["pts"].max()
    out = []
    for _, r in base.iterrows():
        p = 0.0
        if (r["bank_id"], r["period"]) in by_bp.index:
            p = max(p, by_bp.loc[(r["bank_id"], r["period"])])
        if r["bank_id"] in by_bank.index:
            p = max(p, by_bank.loc[r["bank_id"]] * 0.6)  # bank-wide -> partial weight
        out.append(p)
    return pd.Series(out, index=base.index).clip(0, 100)


def _level_from_score(score: float) -> str:
    if pd.isna(score):
        return "LOW"
    if score <= 25:
        return "LOW"
    if score <= 50:
        return "MEDIUM"
    if score <= 75:
        return "HIGH"
    return "CRITICAL"


def bank_level_summary(scores: pd.DataFrame) -> pd.DataFrame:
    """Collapse to one row per bank using its latest period (audit ranking view)."""
    if scores is None or scores.empty:
        return pd.DataFrame()
    latest = (scores.sort_values("period_ts")
              .groupby("bank_id", as_index=False).tail(1)
              .sort_values("final_risk_score", ascending=False)
              .reset_index(drop=True))
    return latest


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    from .feature_engineering import build_features, compute_systemic_stress
    from .rule_engine import evaluate_rules
    from .anomaly_detection import run_isolation_forest
    from .clustering import run_kmeans, latest_snapshot
    res = load_all(DATA_ROOT, use_cache=True)
    feats = build_features(res.wide["quarterly"], "quarterly")
    rf = evaluate_rules(feats)
    an = run_isolation_forest(feats, feats.attrs["base_metrics"])
    cl = run_kmeans(latest_snapshot(feats), feats.attrs["base_metrics"])
    ss = compute_systemic_stress(feats)
    scores = compute_risk_scores(feats, rf, an.table, cl.table, None, ss)
    print(scores[["bank_id", "period", "final_risk_score", "risk_level"]].head(15))
    print("\nTop banks:\n", bank_level_summary(scores)[
        ["bank_id", "final_risk_score", "risk_level"]].head(10))
