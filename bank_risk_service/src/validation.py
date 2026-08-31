"""Automated data validation and special-case detection.

Produces a long findings table (one row per issue) covering: missing periods,
duplicate bank-periods, type errors, abnormal negatives, ratios out of plausible
range, missing legally-required metrics, and special supervisory cases (new banks,
data gaps, unit jumps, hot credit growth vs flat capital/liquidity, NPL falling while
group-2/provisions move adversely, profit up while operations deteriorate, etc.).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .rule_engine import load_institution_types
from .utils import LOG, load_config

# Plausible ranges for ratio metrics (%). Outside -> validation finding.
# Áp cho giá trị TCTD BÁO CÁO: dữ liệu vẫn giữ nguyên để KTV xem xét, chỉ gắn cờ.
# (Tỷ lệ do code tự suy ra được chặn sớm hơn ở feature_engineering.derive_ratios.)
PLAUSIBLE_RANGES = {
    "car_solo": (0, 60), "car_consolidated": (0, 60), "car_tier1": (0, 60),
    "ldr": (0, 200), "npl_ratio": (0, 100), "group2_ratio": (0, 100),
    "roa": (-20, 20), "roe": (-100, 100), "nim": (-10, 20), "cir": (0, 300),
    "liquidity_reserve_ratio": (0, 100), "st_funding_for_mlt_loans": (0, 100),
    "solvency_30d_vnd": (0, 500), "solvency_30d_fx": (0, 5000), "equity_to_assets": (0, 60),
}
# Amounts that should never be negative.
NON_NEGATIVE = ["total_assets", "equity", "customer_loans", "deposits", "npl_amount",
                "provisions", "charter_capital", "rwa", "hqla"]


def _finding(category, severity, bank_id, period, metric, message):
    return {"category": category, "severity": severity, "bank_id": bank_id,
            "period": period, "metric": metric, "message": message}


def validate_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Structural checks on the long panel (duplicates, missing periods)."""
    findings = []
    if panel is None or panel.empty:
        return pd.DataFrame(columns=["category", "severity", "bank_id", "period", "metric", "message"])

    # Duplicate bank-period-metric (per frequency).
    dup = panel.duplicated(subset=["bank_id", "frequency", "period", "metric_name"], keep=False)
    if dup.any():
        for (bid, freq, period, metric), _ in panel[dup].groupby(
                ["bank_id", "frequency", "period", "metric_name"]):
            findings.append(_finding("DUPLICATE", "MEDIUM", bid, period, metric,
                                     f"Trùng bản ghi ({freq})"))

    # Missing periods per bank per frequency (gaps in the time index).
    for (bid, freq), sub in panel.groupby(["bank_id", "frequency"]):
        periods = sub.drop_duplicates("period").sort_values("period_ts")
        ts = periods["period_ts"].dropna()
        if len(ts) < 3:
            findings.append(_finding("SHORT_HISTORY", "HIGH", bid, None, None,
                                     f"Lịch sử ngắn ({len(ts)} kỳ, {freq}) — ngân hàng mới/thiếu dữ liệu"))
            continue
        gaps = _detect_gaps(ts, freq)
        for g in gaps:
            findings.append(_finding("MISSING_PERIOD", "MEDIUM", bid, g, None,
                                     f"Thiếu kỳ báo cáo ({freq}) quanh {g}"))
    return pd.DataFrame(findings)


def _detect_gaps(ts: pd.Series, freq: str) -> list[str]:
    ts = ts.sort_values()
    if freq == "monthly":
        step = pd.DateOffset(months=1)
    elif freq == "quarterly":
        step = pd.DateOffset(months=3)
    elif freq == "yearly":
        step = pd.DateOffset(years=1)
    else:
        return []  # daily (month-end snapshots) — skip strict gap check
    gaps = []
    cur = ts.iloc[0]
    end = ts.iloc[-1]
    have = set(ts.dt.to_period("M").astype(str)) if freq != "yearly" else set(ts.dt.year.astype(str))
    while cur <= end:
        key = cur.to_period("M").__str__() if freq != "yearly" else str(cur.year)
        if key not in have:
            gaps.append(key)
        cur = cur + step
    return gaps[:12]


def validate_features(features: pd.DataFrame) -> pd.DataFrame:
    """Value-level checks on the wide feature table."""
    findings = []
    if features is None or features.empty:
        return pd.DataFrame(columns=["category", "severity", "bank_id", "period", "metric", "message"])

    legal_scope = _legal_metric_scope()
    inst_types, _ = load_institution_types()
    for _, row in features.iterrows():
        bid, period = row["bank_id"], row["period"]
        # Negatives.
        for m in NON_NEGATIVE:
            if m in features.columns:
                v = row.get(m)
                if pd.notna(v) and v < 0:
                    findings.append(_finding("NEGATIVE", "HIGH", bid, period, m,
                                             f"{m} âm bất thường: {v:.2f}"))
        # Out-of-range ratios.
        for m, (lo, hi) in PLAUSIBLE_RANGES.items():
            if m in features.columns:
                v = row.get(m)
                if pd.notna(v) and (v < lo or v > hi):
                    findings.append(_finding("OUT_OF_RANGE", "MEDIUM", bid, period, m,
                                             f"{m}={v:.2f} ngoài khoảng hợp lý [{lo}, {hi}]"))

    # Missing legally-required metrics (per bank, share of periods missing).
    for m, types in legal_scope.items():
        if m not in features.columns:
            findings.append(_finding("MISSING_LEGAL_METRIC", "HIGH", None, None, m,
                                     f"Thiếu hoàn toàn chỉ tiêu pháp lý: {m}"))
            continue
        miss = features.groupby("bank_id")[m].apply(lambda x: x.isna().mean())
        for bid, frac in miss.items():
            # Chỉ tiêu không áp cho loại hình của đơn vị thì thiếu số KHÔNG phải
            # data gap (vd QĐ 682 để trống ô LDR của công ty tài chính/cho thuê
            # tài chính) — cùng cách xử lý với rule_engine._evaluate_tiered_rule.
            if types is not None and inst_types.get(bid) not in types:
                continue
            if frac >= 0.5:
                sev = "CRITICAL" if frac >= 0.8 else "HIGH"
                findings.append(_finding("DATA_GAP_LEGAL", sev, bid, None, m,
                                         f"Thiếu {frac*100:.0f}% kỳ của chỉ tiêu pháp lý {m}"))

    findings.extend(_derived_ratio_gaps(features))
    return pd.DataFrame(findings)


def _derived_ratio_gaps(features: pd.DataFrame) -> list[dict]:
    """Chỉ tiêu bị BỎ vì suy ra từ thành phần không đỡ nổi tỷ lệ.

    ``feature_engineering.derive_ratios`` không đánh giá các tỷ lệ này (xem docstring
    ở đó). Gộp theo đơn vị + chỉ tiêu và báo lại để KTV biết vì sao ô trống, thay vì
    để chỉ tiêu biến mất im lặng. Mức INFO: đây là chỉ tiêu KHÔNG ĐÁNH GIÁ ĐƯỢC, chưa
    phải kết luận dữ liệu sai.
    """
    gaps = features.attrs.get("derived_ratio_gaps")
    if gaps is None or gaps.empty:
        return []
    out = []
    for (bid, metric), sub in gaps.groupby(["bank_id", "metric"]):
        periods = sorted(str(p) for p in sub["period"].dropna().unique())
        shown = ", ".join(periods[:3]) + ("…" if len(periods) > 3 else "")
        out.append(_finding(
            "RATIO_NOT_EVALUATED", "INFO", bid, None, metric,
            f"KHÔNG đánh giá {metric} ở {len(sub)} kỳ ({shown}): "
            f"{sub['message'].iloc[0]}"))
    return out


def detect_special_cases(features: pd.DataFrame) -> pd.DataFrame:
    """Supervisory special-case detection (per bank-period)."""
    findings = []
    if features is None or features.empty:
        return pd.DataFrame(columns=["category", "severity", "bank_id", "period", "metric", "message"])

    df = features.sort_values(["bank_id", "period_ts"])
    for bid, sub in df.groupby("bank_id"):
        sub = sub.reset_index(drop=True)
        n_missing = sub.drop(columns=[c for c in ["bank_id", "bank_name", "period", "period_ts"]
                                      if c in sub.columns]).isna().mean(axis=1)
        for i, frac in n_missing.items():
            if frac >= 0.6:
                findings.append(_finding("HIGH_MISSING_PERIOD", "MEDIUM", bid,
                                         sub.loc[i, "period"], None,
                                         f"Bank-period thiếu {frac*100:.0f}% chỉ tiêu"))
        _special_credit_liquidity(sub, bid, findings)
        _extended_credit_flags(sub, bid, findings)
        _extended_liquidity_flags(sub, bid, findings)
        _extended_fraud_flags(sub, bid, findings)
    return pd.DataFrame(findings)


def _special_credit_liquidity(sub: pd.DataFrame, bid: str, findings: list):
    """Detect the named supervisory red-flag patterns within one bank's series."""
    def chg(col):
        return sub[col].pct_change() * 100 if col in sub.columns else pd.Series(np.nan, index=sub.index)

    credit_g = chg("customer_loans")
    cap_g = chg("equity")
    liq = sub["liquidity_reserve_ratio"] if "liquidity_reserve_ratio" in sub.columns else pd.Series(np.nan, index=sub.index)
    npl = sub["npl_ratio"] if "npl_ratio" in sub.columns else pd.Series(np.nan, index=sub.index)
    group2 = sub["group2_ratio"] if "group2_ratio" in sub.columns else pd.Series(np.nan, index=sub.index)
    prov = chg("provisions")
    profit = chg("profit_before_tax")
    toi_g = chg("toi")
    deposits_g = chg("deposits")

    for i in range(1, len(sub)):
        period = sub.loc[i, "period"]
        # Hot credit growth while capital/liquidity not keeping up.
        if pd.notna(credit_g.iloc[i]) and credit_g.iloc[i] > 10:
            if (pd.notna(cap_g.iloc[i]) and cap_g.iloc[i] < credit_g.iloc[i] / 2) or \
               (pd.notna(liq.iloc[i]) and pd.notna(liq.iloc[i-1]) and liq.iloc[i] < liq.iloc[i-1]):
                findings.append(_finding("HOT_CREDIT_WEAK_SUPPORT", "HIGH", bid, period, None,
                                         "Tăng trưởng tín dụng cao trong khi vốn/thanh khoản không tăng tương ứng"))
        # NPL falls while group-2 rises or provisions drop (possible masking).
        if pd.notna(npl.iloc[i]) and pd.notna(npl.iloc[i-1]) and npl.iloc[i] < npl.iloc[i-1]:
            if (pd.notna(group2.iloc[i]) and pd.notna(group2.iloc[i-1]) and group2.iloc[i] > group2.iloc[i-1]) or \
               (pd.notna(prov.iloc[i]) and prov.iloc[i] < -10):
                findings.append(_finding("NPL_DROP_DIVERGENCE", "HIGH", bid, period, None,
                                         "Nợ xấu giảm nhưng nợ nhóm 2/dự phòng biến động ngược chiều"))
        # Profit up while operating income or asset quality deteriorates.
        if pd.notna(profit.iloc[i]) and profit.iloc[i] > 10:
            if (pd.notna(toi_g.iloc[i]) and toi_g.iloc[i] < 0) or \
               (pd.notna(npl.iloc[i]) and pd.notna(npl.iloc[i-1]) and npl.iloc[i] > npl.iloc[i-1]):
                findings.append(_finding("PROFIT_UP_OPS_DOWN", "MEDIUM", bid, period, None,
                                         "Lợi nhuận tăng nhưng thu nhập hoạt động/chất lượng tài sản xấu đi"))
        # High LDR with falling deposits.
        ldr_val = sub["ldr"].iloc[i] if "ldr" in sub.columns else np.nan
        if pd.notna(ldr_val) and ldr_val > 80 and pd.notna(deposits_g.iloc[i]) and deposits_g.iloc[i] < -5:
            findings.append(_finding("LDR_HIGH_DEPOSIT_STRESS", "HIGH", bid, period, None,
                                     "LDR cao và tiền gửi giảm mạnh — căng thẳng thanh khoản"))


# --------------------------------------------------------------------------- #
# Bộ cờ đỏ mở rộng (readme_explain_bo_sung.docx §13.2–13.4)
#
# Nguyên tắc §13.1: chỉ tiêu CHƯA có ngưỡng pháp lý dùng biến động chuỗi thời
# gian / chênh lệch tương đối, KHÔNG tự gán ngưỡng bắt buộc. Các cờ này ở mức
# MEDIUM/HIGH mang tính REVIEW_REQUIRED — KTV kiểm tra hồ sơ, không phải kết luận.
# --------------------------------------------------------------------------- #
def _series_of(sub: pd.DataFrame, col: str) -> pd.Series:
    return (pd.to_numeric(sub[col], errors="coerce") if col in sub.columns
            else pd.Series(np.nan, index=sub.index))


def _pct_chg(sub: pd.DataFrame, col: str) -> pd.Series:
    """% thay đổi kỳ-liền-kỳ trên giá trị hợp lệ gần nhất (khớp thiết kế ffill
    của feature_engineering cho chỉ tiêu quý nằm trên lưới tháng)."""
    s = _series_of(sub, col)
    return s.ffill().pct_change() * 100


def _level(sub: pd.DataFrame, col: str) -> pd.Series:
    """Chuỗi MỨC đã ffill: chỉ tiêu quý/năm nằm trên lưới tháng chỉ có số ở kỳ
    chốt — so sánh dòng-liền-dòng trên giá trị thô sẽ không bao giờ thỏa vì một
    vế luôn NaN. Lấy giá trị hợp lệ gần nhất; tại kỳ có số mới, phép so sánh
    "mới vs giá trị đã biết trước đó" đúng ngữ nghĩa giám sát."""
    return _series_of(sub, col).ffill()


def _rising_2(series: pd.Series) -> pd.Series:
    """True tại dòng mà 3 quan sát KHÔNG-NaN gần nhất (kể cả dòng này) tăng
    nghiêm ngặt — "tăng liên tục 2 kỳ BÁO CÁO", chịu được lưới tháng có chỉ
    tiêu quý (NaN xen kẽ giữa các kỳ chốt)."""
    valid = series.dropna()
    out = pd.Series(False, index=series.index)
    vals = valid.to_numpy()
    for k in range(2, len(vals)):
        if vals[k] > vals[k - 1] > vals[k - 2]:
            out.loc[valid.index[k]] = True
    return out


def _extended_credit_flags(sub: pd.DataFrame, bid: str, findings: list):
    """Tín hiệu/cờ đỏ tín dụng bổ sung (§13.2)."""
    loans_g = _pct_chg(sub, "customer_loans")
    tier1_g = _pct_chg(sub, "tier1_capital")
    own_cap_g = _pct_chg(sub, "own_capital_solo")
    rwa_credit_g = _pct_chg(sub, "rwa_credit")
    npl_amount_g = _pct_chg(sub, "npl_amount")
    prov_g = _pct_chg(sub, "provisions")
    accr_g = _pct_chg(sub, "accrued_interest")
    car = _level(sub, "car_solo")
    npl = _level(sub, "npl_ratio")
    g2 = _level(sub, "group2_ratio")
    g5 = _level(sub, "group5_ratio")
    llr = _level(sub, "llr_coverage")
    accr_days = _level(sub, "accrued_interest_days")
    g2_rising = _rising_2(_series_of(sub, "group2_ratio"))
    conc_cols = ["risky_sector_ratio", "real_estate_loan_ratio", "unsecured_loan_ratio",
                 "large_borrower_ratio", "largest_customer_group_ratio"]
    conc = {c: _level(sub, c) for c in conc_cols}

    for i in range(1, len(sub)):
        period = sub.loc[i, "period"]
        # CREDIT_GROWTH_CAPITAL_GAP: dư nợ tăng nhanh hơn vốn cấp 1/vốn tự có
        # hoặc CAR giảm trong khi tín dụng nóng.
        if pd.notna(loans_g.iloc[i]) and loans_g.iloc[i] > 10:
            cap_lag = ((pd.notna(tier1_g.iloc[i]) and tier1_g.iloc[i] < loans_g.iloc[i] / 2)
                       or (pd.notna(own_cap_g.iloc[i]) and own_cap_g.iloc[i] < loans_g.iloc[i] / 2))
            car_down = (pd.notna(car.iloc[i]) and pd.notna(car.iloc[i - 1])
                        and car.iloc[i] < car.iloc[i - 1] - 0.2)
            if cap_lag or car_down:
                findings.append(_finding(
                    "CREDIT_GROWTH_CAPITAL_GAP", "HIGH", bid, period, "customer_loans",
                    f"Dư nợ tăng {loans_g.iloc[i]:.1f}% nhanh hơn vốn cấp 1/vốn tự có hoặc CAR giảm "
                    "— sức hấp thụ tổn thất không theo kịp tăng trưởng"))
        # CREDIT_GROWTH_RWA_DIVERGENCE: dư nợ tăng mạnh nhưng RWA tín dụng tăng
        # thấp bất thường -> kiểm tra hệ số rủi ro / chất lượng dữ liệu.
        if (pd.notna(loans_g.iloc[i]) and loans_g.iloc[i] > 10
                and pd.notna(rwa_credit_g.iloc[i]) and rwa_credit_g.iloc[i] < loans_g.iloc[i] / 3):
            findings.append(_finding(
                "CREDIT_GROWTH_RWA_DIVERGENCE", "MEDIUM", bid, period, "rwa_credit",
                f"Dư nợ tăng {loans_g.iloc[i]:.1f}% nhưng RWA tín dụng chỉ tăng "
                f"{rwa_credit_g.iloc[i]:.1f}% — REVIEW hệ số rủi ro/cơ cấu tài sản/dữ liệu"))
        # NPL_GROUP2_MIGRATION: nợ nhóm 2 tăng liên tục (dấu hiệu dẫn trước nợ xấu)
        # hoặc nợ xấu giảm nhưng nhóm 2 không giảm tương ứng.
        if g2_rising.iloc[i]:
            findings.append(_finding(
                "NPL_GROUP2_MIGRATION", "MEDIUM", bid, period, "group2_ratio",
                f"Nợ nhóm 2 tăng liên tục 2 kỳ báo cáo (hiện {g2.iloc[i]:.2f}%) "
                "— nguy cơ chuyển dịch sang nhóm 3-5"))
        elif (pd.notna(npl.iloc[i]) and pd.notna(npl.iloc[i - 1]) and npl.iloc[i] < npl.iloc[i - 1]
                and pd.notna(g2.iloc[i]) and pd.notna(g2.iloc[i - 1]) and g2.iloc[i] >= g2.iloc[i - 1] + 0.2):
            findings.append(_finding(
                "NPL_GROUP2_MIGRATION", "MEDIUM", bid, period, "group2_ratio",
                "Nợ xấu giảm nhưng nợ nhóm 2 không giảm tương ứng — theo dõi chuyển nhóm nợ"))
        # PROVISION_LAG: nợ xấu/nhóm 5 tăng nhưng dự phòng tăng chậm, bao phủ suy giảm.
        npl_up = pd.notna(npl_amount_g.iloc[i]) and npl_amount_g.iloc[i] > 10
        g5_up = (pd.notna(g5.iloc[i]) and pd.notna(g5.iloc[i - 1])
                 and g5.iloc[i] > g5.iloc[i - 1] + 0.2)
        if (npl_up or g5_up):
            prov_slow = pd.notna(prov_g.iloc[i]) and prov_g.iloc[i] < (npl_amount_g.iloc[i] / 2
                                                                       if npl_up else 0)
            llr_down = (pd.notna(llr.iloc[i]) and pd.notna(llr.iloc[i - 1])
                        and llr.iloc[i] < llr.iloc[i - 1] - 2)
            if prov_slow or llr_down:
                findings.append(_finding(
                    "PROVISION_LAG", "HIGH", bid, period, "provisions",
                    "Nợ xấu/nợ nhóm 5 tăng nhưng dự phòng tăng chậm — tỷ lệ bao phủ suy giảm"))
        # CONCENTRATION_BUILDUP: tỷ trọng tập trung tăng nhanh hơn tổng dư nợ (+2đ%).
        for c, s in conc.items():
            if pd.notna(s.iloc[i]) and pd.notna(s.iloc[i - 1]) and s.iloc[i] > s.iloc[i - 1] + 2:
                findings.append(_finding(
                    "CONCENTRATION_BUILDUP", "MEDIUM", bid, period, c,
                    f"Tỷ trọng tập trung {c} tăng {s.iloc[i] - s.iloc[i - 1]:.1f}đ% "
                    f"({s.iloc[i - 1]:.1f}% → {s.iloc[i]:.1f}%) — nhanh hơn tổng dư nợ"))
        # ACCRUED_INTEREST_CREDIT_STRESS: lãi dự thu/số ngày lãi phải thu tăng cùng
        # lúc chất lượng nợ xấu đi -> khả năng thu lãi suy giảm.
        accr_up = ((pd.notna(accr_g.iloc[i]) and accr_g.iloc[i] > 10)
                   or (pd.notna(accr_days.iloc[i]) and pd.notna(accr_days.iloc[i - 1])
                       and accr_days.iloc[i] > accr_days.iloc[i - 1] + 5))
        quality_down = ((pd.notna(g2.iloc[i]) and pd.notna(g2.iloc[i - 1]) and g2.iloc[i] > g2.iloc[i - 1])
                        or (pd.notna(npl.iloc[i]) and pd.notna(npl.iloc[i - 1]) and npl.iloc[i] > npl.iloc[i - 1]))
        if accr_up and quality_down:
            findings.append(_finding(
                "ACCRUED_INTEREST_CREDIT_STRESS", "HIGH", bid, period, "accrued_interest",
                "Lãi dự thu/số ngày lãi phải thu tăng cùng lúc nợ nhóm 2/nợ xấu tăng "
                "— khả năng thu lãi suy giảm"))


def _extended_liquidity_flags(sub: pd.DataFrame, bid: str, findings: list):
    """Tín hiệu/cờ đỏ thanh khoản bổ sung (§13.3)."""
    hqla_g = _pct_chg(sub, "hqla")
    outflow_g = _pct_chg(sub, "net_cash_outflow_30d")
    deposits_g = _pct_chg(sub, "deposits")
    papers_g = _pct_chg(sub, "valuable_papers_issued")
    interbank_g = _pct_chg(sub, "interbank_funding")
    mlt_loans_g = _pct_chg(sub, "medium_long_term_loans")
    mlt_fund_g = _pct_chg(sub, "medium_long_term_funding")
    casa = _level(sub, "casa")
    ldr = _level(sub, "ldr")
    stf = _level(sub, "st_funding_for_mlt_loans")
    stf_rising = _rising_2(_series_of(sub, "st_funding_for_mlt_loans"))
    sol_vnd = _level(sub, "solvency_30d_vnd")
    sol_fx = _level(sub, "solvency_30d_fx")
    gap_ratio = _level(sub, "rate_sensitive_gap_ratio")
    liq_reserve = _level(sub, "liquidity_reserve_ratio")

    for i in range(1, len(sub)):
        period = sub.loc[i, "period"]
        # HQLA_OUTFLOW_STRESS: HQLA giảm trong khi dòng tiền ra ròng 30 ngày tăng.
        if (pd.notna(hqla_g.iloc[i]) and hqla_g.iloc[i] < -5
                and pd.notna(outflow_g.iloc[i]) and outflow_g.iloc[i] > 5):
            findings.append(_finding(
                "HQLA_OUTFLOW_STRESS", "HIGH", bid, period, "hqla",
                f"HQLA giảm {hqla_g.iloc[i]:.1f}% trong khi dòng tiền ra ròng 30 ngày tăng "
                f"{outflow_g.iloc[i]:.1f}% — đệm chi trả suy giảm nhanh"))
        # DEPOSIT_CASA_STRESS: tiền gửi/CASA giảm liên tiếp khi LDR ở vùng cao.
        dep_down_2 = (pd.notna(deposits_g.iloc[i]) and deposits_g.iloc[i] < 0
                      and pd.notna(deposits_g.iloc[i - 1]) and deposits_g.iloc[i - 1] < 0)
        casa_down = (pd.notna(casa.iloc[i]) and pd.notna(casa.iloc[i - 1])
                     and casa.iloc[i] < casa.iloc[i - 1] - 1)
        if (dep_down_2 or casa_down) and pd.notna(ldr.iloc[i]) and ldr.iloc[i] > 80:
            findings.append(_finding(
                "DEPOSIT_CASA_STRESS", "HIGH", bid, period, "deposits",
                "Tiền gửi khách hàng/CASA giảm liên tiếp trong khi LDR duy trì vùng cao"))
        # WHOLESALE_FUNDING_SUBSTITUTION: tiền gửi giảm nhưng GTCG/vay TCTD tăng đột biến.
        wholesale_spike = ((pd.notna(papers_g.iloc[i]) and papers_g.iloc[i] > 15)
                           or (pd.notna(interbank_g.iloc[i]) and interbank_g.iloc[i] > 20))
        if pd.notna(deposits_g.iloc[i]) and deposits_g.iloc[i] < 0 and wholesale_spike:
            findings.append(_finding(
                "WHOLESALE_FUNDING_SUBSTITUTION", "MEDIUM", bid, period, "wholesale_funding_share",
                "Tiền gửi khách hàng suy giảm nhưng phát hành GTCG/vay TCTD khác tăng đột biến "
                "— thay thế bằng nguồn vốn bán buôn kém ổn định hơn"))
            # FUNDING_SOURCE_SWAP (§13.4.1): nếu đồng thời LDR/khả năng chi trả cuối kỳ
            # vẫn "đẹp" (ổn định) thì nghi làm ổn định chỉ tiêu bằng hoán đổi nguồn.
            ldr_stable = (pd.notna(ldr.iloc[i]) and pd.notna(ldr.iloc[i - 1])
                          and abs(ldr.iloc[i] - ldr.iloc[i - 1]) <= 2)
            sol_stable = (pd.notna(sol_vnd.iloc[i]) and pd.notna(sol_vnd.iloc[i - 1])
                          and sol_vnd.iloc[i] >= sol_vnd.iloc[i - 1] - 2)
            if ldr_stable or sol_stable:
                findings.append(_finding(
                    "FUNDING_SOURCE_SWAP", "MEDIUM", bid, period, "wholesale_funding_share",
                    "Tiền gửi KH/CASA giảm nhưng GTCG/vay TCTD tăng đột biến giúp LDR/thanh khoản "
                    "cuối kỳ vẫn ổn định — REVIEW khả năng hoán đổi nguồn để làm đẹp chỉ tiêu"))
        # MATURITY_MISMATCH_BUILDUP: dư nợ TDH tăng nhanh hơn nguồn vốn TDH, hoặc
        # tỷ lệ vốn ngắn hạn cho vay TDH tăng liên tục.
        mlt_diverge = (pd.notna(mlt_loans_g.iloc[i]) and pd.notna(mlt_fund_g.iloc[i])
                       and mlt_loans_g.iloc[i] > mlt_fund_g.iloc[i] + 5 and mlt_loans_g.iloc[i] > 5)
        if mlt_diverge or stf_rising.iloc[i]:
            findings.append(_finding(
                "MATURITY_MISMATCH_BUILDUP", "MEDIUM", bid, period, "st_funding_for_mlt_loans",
                "Dư nợ trung-dài hạn tăng nhanh hơn nguồn vốn trung-dài hạn / tỷ lệ vốn ngắn hạn "
                "cho vay TDH tăng liên tục — lệch kỳ hạn tích tụ"))
        # FX_LIQUIDITY_DIVERGENCE: khả năng chi trả VND ổn định nhưng ngoại tệ suy giảm.
        if (pd.notna(sol_fx.iloc[i]) and pd.notna(sol_fx.iloc[i - 1])
                and sol_fx.iloc[i] < sol_fx.iloc[i - 1] - 5
                and pd.notna(sol_vnd.iloc[i]) and pd.notna(sol_vnd.iloc[i - 1])
                and sol_vnd.iloc[i] >= sol_vnd.iloc[i - 1] - 1):
            findings.append(_finding(
                "FX_LIQUIDITY_DIVERGENCE", "MEDIUM", bid, period, "solvency_30d_fx",
                "Khả năng chi trả VND ổn định nhưng khả năng chi trả ngoại tệ suy giảm "
                "— theo dõi dòng tiền ra ngoại tệ"))
        # INTEREST_RATE_GAP_LIQUIDITY: chênh lệch TS-Nợ nhạy cảm lãi suất lớn đồng thời
        # bộ đệm thanh khoản giảm (ngưỡng 30% mang tính phân tích — REVIEW_REQUIRED).
        if (pd.notna(gap_ratio.iloc[i]) and abs(gap_ratio.iloc[i]) > 30
                and pd.notna(liq_reserve.iloc[i]) and pd.notna(liq_reserve.iloc[i - 1])
                and liq_reserve.iloc[i] < liq_reserve.iloc[i - 1] - 1):
            findings.append(_finding(
                "INTEREST_RATE_GAP_LIQUIDITY", "MEDIUM", bid, period, "rate_sensitive_gap_ratio",
                f"Chênh lệch TS-Nợ nhạy cảm lãi suất lớn ({gap_ratio.iloc[i]:.0f}% VCSH) đồng thời "
                "dự trữ thanh khoản giảm — nguy cơ chi phí vốn/rút tiền (REVIEW)"))


def _extended_fraud_flags(sub: pd.DataFrame, bid: str, findings: list):
    """Cờ đỏ gian lận BCTC mở rộng (§13.4.1) — phát hiện phân kỳ/làm đẹp số liệu."""
    accr_g = _pct_chg(sub, "accrued_interest")
    profit_g = _pct_chg(sub, "profit_before_tax")
    toi_g = _pct_chg(sub, "toi")
    nii_g = _pct_chg(sub, "net_interest_income")
    prov_g = _pct_chg(sub, "provisions")
    offbal_g = _pct_chg(sub, "off_balance_commitments")
    tier1_g = _pct_chg(sub, "tier1_capital")
    own_cap_g = _pct_chg(sub, "own_capital_solo")
    rwa_g = _pct_chg(sub, "rwa")
    npl = _level(sub, "npl_ratio")
    g2 = _level(sub, "group2_ratio")
    g5 = _level(sub, "group5_ratio")
    llr = _level(sub, "llr_coverage")
    bad_offbal = _level(sub, "bad_offbalance_ratio")
    accr_days = _level(sub, "accrued_interest_days")
    nim = _level(sub, "nim")
    car = _level(sub, "car_solo")
    charter = _level(sub, "charter_capital")
    charter_real = _level(sub, "charter_capital_real")

    for i in range(1, len(sub)):
        period = sub.loc[i, "period"]
        # ACCRUED_INTEREST_PROFIT_DIVERGENCE: lãi dự thu tăng mạnh; lợi nhuận/NII tăng
        # nhưng TOI/NIM không cải thiện tương ứng -> nghi ghi nhận thu nhập chưa thu được.
        accr_spike = ((pd.notna(accr_g.iloc[i]) and accr_g.iloc[i] > 15)
                      or (pd.notna(accr_days.iloc[i]) and pd.notna(accr_days.iloc[i - 1])
                          and accr_days.iloc[i] > accr_days.iloc[i - 1] + 10))
        income_up = ((pd.notna(profit_g.iloc[i]) and profit_g.iloc[i] > 10)
                     or (pd.notna(nii_g.iloc[i]) and nii_g.iloc[i] > 10))
        support_flat = ((pd.notna(toi_g.iloc[i]) and toi_g.iloc[i] <= 0)
                        or (pd.notna(nim.iloc[i]) and pd.notna(nim.iloc[i - 1])
                            and nim.iloc[i] <= nim.iloc[i - 1]))
        if accr_spike and income_up and support_flat:
            findings.append(_finding(
                "ACCRUED_INTEREST_PROFIT_DIVERGENCE", "HIGH", bid, period, "accrued_interest",
                "Lãi dự thu tăng mạnh; lợi nhuận/NII tăng nhưng TOI/NIM không cải thiện "
                "— nghi ghi nhận thu nhập chưa thu được hoặc kéo dài lãi dự thu"))
        # NPL_GROUP2_PROVISION_DIVERGENCE: NPL giảm nhưng nhóm 2/nhóm 5 tăng; hoặc nợ
        # xấu tăng trong khi dự phòng/LLR giảm.
        npl_down = pd.notna(npl.iloc[i]) and pd.notna(npl.iloc[i - 1]) and npl.iloc[i] < npl.iloc[i - 1]
        npl_up = pd.notna(npl.iloc[i]) and pd.notna(npl.iloc[i - 1]) and npl.iloc[i] > npl.iloc[i - 1]
        g2_or_g5_up = ((pd.notna(g2.iloc[i]) and pd.notna(g2.iloc[i - 1]) and g2.iloc[i] > g2.iloc[i - 1] + 0.2)
                       or (pd.notna(g5.iloc[i]) and pd.notna(g5.iloc[i - 1]) and g5.iloc[i] > g5.iloc[i - 1] + 0.2))
        prov_down = ((pd.notna(prov_g.iloc[i]) and prov_g.iloc[i] < -5)
                     or (pd.notna(llr.iloc[i]) and pd.notna(llr.iloc[i - 1])
                         and llr.iloc[i] < llr.iloc[i - 1] - 5))
        if (npl_down and g2_or_g5_up) or (npl_up and prov_down):
            findings.append(_finding(
                "NPL_GROUP2_PROVISION_DIVERGENCE", "HIGH", bid, period, "npl_ratio",
                "Phân kỳ NPL – nhóm 2/nhóm 5 – dự phòng: nghi phân loại nợ hoặc trích lập "
                "dự phòng chưa phản ánh đầy đủ rủi ro"))
        # OFFBALANCE_RISK_SHIFT: NPL nội bảng giảm nhưng cam kết ngoại bảng /
        # tỷ lệ cam kết nhóm 3-5 tăng -> nghi dịch chuyển rủi ro ra ngoài bảng.
        offbal_up = ((pd.notna(offbal_g.iloc[i]) and offbal_g.iloc[i] > 15)
                     or (pd.notna(bad_offbal.iloc[i]) and pd.notna(bad_offbal.iloc[i - 1])
                         and bad_offbal.iloc[i] > bad_offbal.iloc[i - 1] + 0.5))
        if npl_down and offbal_up:
            findings.append(_finding(
                "OFFBALANCE_RISK_SHIFT", "MEDIUM", bid, period, "off_balance_commitments",
                "NPL nội bảng giảm nhưng cam kết ngoại bảng/cam kết nhóm 3-5 tăng "
                "— nghi dịch chuyển nghĩa vụ/rủi ro ra ngoài bảng"))
        # CAPITAL_COMPONENT_MISMATCH: CAR tăng trong khi vốn cấp 1/vốn tự có giảm hoặc
        # RWA tăng; hoặc vốn điều lệ và giá trị thực chênh lệch đáng kể (>10%).
        car_up = pd.notna(car.iloc[i]) and pd.notna(car.iloc[i - 1]) and car.iloc[i] > car.iloc[i - 1] + 0.2
        cap_down = ((pd.notna(tier1_g.iloc[i]) and tier1_g.iloc[i] < -1)
                    or (pd.notna(own_cap_g.iloc[i]) and own_cap_g.iloc[i] < -1))
        rwa_up = pd.notna(rwa_g.iloc[i]) and rwa_g.iloc[i] > 5
        charter_gap = (pd.notna(charter.iloc[i]) and pd.notna(charter_real.iloc[i])
                       and charter.iloc[i] > 0
                       and (charter.iloc[i] - charter_real.iloc[i]) / charter.iloc[i] * 100 > 10)
        if (car_up and (cap_down or rwa_up)) or charter_gap:
            findings.append(_finding(
                "CAPITAL_COMPONENT_MISMATCH", "HIGH", bid, period, "car_solo",
                ("Vốn điều lệ và giá trị thực chênh lệch đáng kể" if charter_gap else
                 "CAR tăng trong khi vốn cấp 1/vốn tự có giảm hoặc RWA tăng")
                + " — nghi sai lệch cấu phần vốn/cách tính RWA"))
        # YEAR_END_LIQUIDITY_WINDOW_DRESSING: tài sản thanh khoản tăng đột biến tại kỳ
        # chốt và đảo chiều ngay kỳ sau (so với trung bình 3 kỳ trước — year_end_spike).
        for col, label in [("hqla", "HQLA"), ("cash_fx_gold", "tiền mặt"),
                           ("deposits_at_sbv", "tiền gửi NHNN"),
                           ("govbond_investment", "TPCP")]:
            s = _series_of(sub, col).ffill()
            if i < 3 or i + 1 >= len(sub):
                continue
            base = s.iloc[i - 3:i].mean()
            if pd.isna(base) or base <= 0 or pd.isna(s.iloc[i]) or pd.isna(s.iloc[i + 1]):
                continue
            spike = s.iloc[i] / base - 1
            reverted = s.iloc[i + 1] < base * 1.1
            if spike > 0.3 and reverted:
                findings.append(_finding(
                    "YEAR_END_LIQUIDITY_WINDOW_DRESSING", "MEDIUM", bid, period, col,
                    f"{label} tăng đột biến +{spike * 100:.0f}% so trung bình 3 kỳ trước rồi đảo "
                    "chiều ngay kỳ sau — nghi làm đẹp thanh khoản tại ngày báo cáo"))
                break   # một cờ/kỳ là đủ — các cấu phần cùng bản chất, tránh đếm trùng


def _legal_metric_scope() -> dict[str, set[str] | None]:
    """Chỉ tiêu pháp lý bắt buộc -> loại hình TCTD bị áp (None = áp cho mọi loại hình).

    Rule ngưỡng theo loại hình chỉ áp cho các loại hình có mặt trong ``tiers_by_type``;
    loại hình để trống nghĩa là QĐ 682/618 KHÔNG quy định chỉ tiêu đó cho họ, nên
    thiếu số không phải là data gap pháp lý. Rule ngưỡng phẳng áp cho mọi đơn vị.
    """
    scope: dict[str, set[str] | None] = {}
    for r in load_config("regulatory_rules").get("rules", []):
        if r.get("severity") != "CRITICAL":
            continue
        metric = r.get("metric")
        tiers = r.get("tiers_by_type")
        types = set(tiers) if tiers else None
        if metric not in scope:
            scope[metric] = types
        elif scope[metric] is None or types is None:
            scope[metric] = None          # một rule bất kỳ áp cho mọi loại hình
        else:
            scope[metric] = scope[metric] | types
    return dict(sorted(scope.items()))


def run_all_validation(panel: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Run every validation layer and return a combined findings table."""
    parts = [validate_panel(panel), validate_features(features), detect_special_cases(features)]
    parts = [p for p in parts if p is not None and not p.empty]
    if not parts:
        return pd.DataFrame(columns=["category", "severity", "bank_id", "period", "metric", "message"])
    out = pd.concat(parts, ignore_index=True)
    LOG.info("Validation: %d findings across %d categories", len(out), out["category"].nunique())
    return out
