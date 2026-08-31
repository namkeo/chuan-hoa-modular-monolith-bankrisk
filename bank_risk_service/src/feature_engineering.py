"""Feature engineering on the bank-period wide table.

Computes CAMELS-aligned ratios (only where not already provided), trend / volatility
features (rolling z-score, QoQ, YoY, drawdown), and systemic features (percentile
rank, deviation from system median, systemic stress index, high-risk-period flag).

Ratios that already exist in the data (e.g. car_solo, ldr, npl_ratio) are kept as-is;
the function only *derives* a ratio when its source ratio column is missing but the
components are present, avoiding double counting.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import DATA_ROOT, LOG, load_config, safe_div

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]

GAP_COLUMNS = ["bank_id", "period", "metric", "reason", "message"]

# Trần của tỷ lệ SUY RA từ hai số dư không âm: vượt trần thì chỉ có thể do mẫu số
# sụp về gần 0, nên tỷ lệ không mang thông tin gì -> coi như không có giá trị.
# CHỈ đặt trần cho những chỗ có căn cứ số học, KHÔNG chặn phía dưới: giá trị âm sâu
# (ROA -247% của SCB, vốn/tài sản -140% của GPBank) là TÍN HIỆU THẬT về đơn vị yếu
# kém, chặn đi là giấu mất phát hiện.
DERIVED_CEILING = {
    # Tiền gửi ~0 (làm tròn ở đơn vị "Tỷ đồng") thì dư nợ/tiền gửi bung tới hàng
    # triệu %. Trên 200% nghĩa là tiền gửi không phải nguồn vốn của đơn vị — đúng
    # thực tế công ty tài chính/cho thuê tài chính, và cũng là lý do QĐ 682 để
    # trống ô LDR của 2 loại hình này.
    "ldr": 200.0,
    # Nợ xấu không thể vượt tổng dư nợ: >100% là phép suy ra đã hỏng.
    "npl_ratio": 100.0,
    # Các tỷ trọng "cấu phần / tổng" (bộ chỉ tiêu bổ sung §13.5): cấu phần là tập
    # con của mẫu số nên >100% chỉ có thể do mẫu số sụp/không cùng phạm vi.
    "short_loan_ratio": 100.0,
    "mlt_loan_ratio": 100.0,
    "provision_to_loans": 100.0,
    "unsecured_loan_ratio": 100.0,
    "risky_sector_ratio": 100.0,
    "large_borrower_ratio": 100.0,
    "wholesale_funding_share": 100.0,
    # Như LDR: tiền gửi ~0 làm tỷ lệ bung nổ — trần phân tích 200%.
    "liquid_assets_to_deposits": 200.0,
}


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Return a column or an all-NaN series of the right length."""
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def _denominator(df: pd.DataFrame, name: str) -> pd.Series:
    """A component usable as a divisor: strictly positive, else NaN.

    Số dư báo cáo bằng 0 nghĩa là khoản mục KHÔNG PHÁT SINH ở đơn vị đó, không phải
    một số chia hợp lệ. Chia cho nó sinh ra inf/tỷ lệ vô nghĩa thay vì "thiếu dữ liệu".
    """
    return _col(df, name).where(lambda s: s > 0)


def _sum_components(*series: pd.Series) -> pd.Series:
    """Tổng các cấu phần, bỏ qua NaN nhưng trả NaN khi KHÔNG có cấu phần nào.

    Dùng cho các biến tổng hợp §13.5 (vd tài sản dễ chuyển đổi = tiền mặt + tiền gửi
    NHNN + TCTD + TPCP): thiếu một cấu phần vẫn tính trên phần còn lại, nhưng thiếu
    tất cả thì phải là "không có dữ liệu" chứ không phải 0.
    """
    return pd.concat(series, axis=1).sum(axis=1, min_count=1)


def derive_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Fill in CAMELS ratios from components when the ratio column is absent.

    Chỉ suy ra tỷ lệ khi các thành phần THỰC SỰ đỡ được nó. Mẫu số bằng 0 — hoặc chỉ
    còn vài chục triệu do làm tròn ở độ chính xác "Tỷ đồng" của biểu — không phải là
    số chia hợp lệ: công ty tài chính/cho thuê tài chính không nhận tiền gửi nên
    ``deposits`` về 0, và 100 × dư nợ / số dư đó từng cho ra LDR tới hàng triệu %
    (CTTC Mirae Asset T11/2023: 100 × 9.994,57 / 0,01 = 99.945.700%).

    Hai lớp chặn: mẫu số phải dương (``_denominator``) và tỷ lệ suy ra không được
    vượt trần số học của nó (``DERIVED_CEILING``). Ô nào không qua thì coi là KHÔNG
    CÓ giá trị, để rule engine / EWS / chấm điểm / biểu đồ bỏ qua thay vì đánh giá
    một con số bịa; trường hợp bị loại ghi vào ``out.attrs["derived_ratio_gaps"]``
    để validation.py báo lại cho KTV, không im lặng.

    Giá trị do TCTD BÁO CÁO không bị đụng tới: chỉ những ô đang trống mới được điền
    (vd LDR 1.995% của SCB là số báo cáo thật, validation vẫn gắn cờ OUT_OF_RANGE).
    """
    out = df.copy()
    gaps: list[dict] = []

    def ensure(name: str, series: pd.Series):
        series = _drop_above_ceiling(out, name, series, gaps)
        if name not in out.columns or out[name].isna().all():
            out[name] = series
        else:
            out[name] = out[name].fillna(series)

    # Tử số: lấy nguyên giá trị báo cáo (0 là một câu trả lời hợp lệ — vd nợ xấu 0
    # nghĩa là tỷ lệ nợ xấu 0%). Mẫu số: bắt buộc dương, xem _denominator().
    equity = _col(out, "equity")
    loans = _col(out, "customer_loans")
    npl = _col(out, "npl_amount")
    provisions = _col(out, "provisions")
    pat = _col(out, "profit_after_tax")
    opex = _col(out, "operating_expense")
    nii = _col(out, "net_interest_income")
    rsa = _col(out, "rate_sensitive_assets")
    rsl = _col(out, "rate_sensitive_liabilities")

    assets_den = _denominator(out, "total_assets")
    equity_den = _denominator(out, "equity")
    loans_den = _denominator(out, "customer_loans")
    deposits_den = _denominator(out, "deposits")
    npl_den = _denominator(out, "npl_amount")
    toi_den = _denominator(out, "toi")

    ensure("equity_to_assets", 100 * equity / assets_den)
    ensure("ldr", 100 * loans / deposits_den)
    ensure("npl_ratio", 100 * npl / loans_den)
    ensure("llr_coverage", 100 * provisions / npl_den)
    ensure("roa", 100 * pat / assets_den)
    ensure("roe", 100 * pat / equity_den)
    ensure("cir", 100 * opex / toi_den)
    ensure("nim", 100 * nii / assets_den)
    # Interest-rate-risk (sensitivity) gap / equity — from the rate-sensitive
    # asset & liability components when the ratio isn't reported directly.
    ensure("rate_sensitive_gap_ratio", 100 * (rsa - rsl) / equity_den)

    # ------------------------------------------------------------------ #
    # Đặc trưng phái sinh bổ sung (readme_explain_bo_sung.docx §13.5)
    # ------------------------------------------------------------------ #
    short_loans = _col(out, "short_term_loans")
    mlt_loans = _col(out, "medium_long_term_loans")
    credit_prov_exp = _col(out, "credit_provision_expense")
    accrued = _col(out, "accrued_interest")
    offbal = _col(out, "off_balance_commitments")
    unsecured = _col(out, "unsecured_loans")
    risky_sector = _col(out, "risky_sector_loans")
    top100 = _col(out, "top100_customer_loans")
    interbank_fund = _col(out, "interbank_funding")
    papers = _col(out, "valuable_papers_issued")
    deposits = _col(out, "deposits")
    cash = _col(out, "cash_fx_gold")
    sbv_dep = _col(out, "deposits_at_sbv")
    interbank_asset = _col(out, "interbank_assets")
    govbond = _col(out, "govbond_investment")
    interest_income_den = _denominator(out, "interest_income")

    # Cơ cấu kỳ hạn danh mục (nhóm 1 tín dụng): tỷ trọng ngắn hạn / trung-dài hạn.
    # mlt_loan_ratio là tỷ lệ CÔNG BỐ — chỉ điền chéo khi ô trống (kiểm tra chéo).
    ensure("short_loan_ratio", 100 * short_loans / loans_den)
    ensure("mlt_loan_ratio", 100 * mlt_loans / loans_den)
    # Dự phòng & chi phí rủi ro tín dụng (nhóm 3): dùng dư nợ CUỐI KỲ làm mẫu số
    # (dư nợ bình quân không có trong biểu — REVIEW nếu cần chuẩn bình quân).
    ensure("provision_to_loans", 100 * provisions / loans_den)
    ensure("credit_cost_ratio", 100 * credit_prov_exp / loans_den)
    # Lãi dự thu & ngoại bảng (nhóm 5): chất lượng thu nhập chưa thu tiền.
    ensure("accrued_interest_to_loans", 100 * accrued / loans_den)
    ensure("accrued_interest_to_interest_income", 100 * accrued / interest_income_den)
    ensure("offbalance_to_assets", 100 * offbal / assets_den)
    # Tập trung tín dụng (nhóm 4): tỷ trọng trên tổng dư nợ, so sánh qua kỳ.
    ensure("unsecured_loan_ratio", 100 * unsecured / loans_den)
    ensure("risky_sector_ratio", 100 * risky_sector / loans_den)
    ensure("large_borrower_ratio", 100 * top100 / loans_den)
    # Ổn định nguồn vốn (thanh khoản nhóm 2): mức phụ thuộc vốn bán buôn trên
    # tổng nguồn huy động chính (tiền gửi KH + vay TCTD + giấy tờ có giá).
    wholesale = _sum_components(interbank_fund, papers)
    funding_base = _sum_components(deposits, interbank_fund, papers).where(lambda s: s > 0)
    ensure("wholesale_funding_share", 100 * wholesale / funding_base)
    # Tài sản dễ chuyển đổi thành tiền (thanh khoản nhóm 4) so với tiền gửi KH.
    liquid_assets = _sum_components(cash, sbv_dep, interbank_asset, govbond)
    ensure("liquid_assets_to_deposits", 100 * liquid_assets / deposits_den)
    # Biến chênh lệch tuyệt đối (Tỷ đồng) — có thể âm, không đặt trần.
    ensure("funding_gap", loans - deposits)
    ensure("interest_sensitive_gap", rsa - rsl)

    out.attrs["derived_ratio_gaps"] = pd.DataFrame(gaps, columns=GAP_COLUMNS)
    return out


def _drop_above_ceiling(df: pd.DataFrame, name: str, derived: pd.Series,
                        gaps: list[dict]) -> pd.Series:
    """Blank out derived values above the metric's ceiling; log each one.

    Vượt trần = mẫu số đã sụp về gần 0 (chỉ còn phần làm tròn) nên tỷ lệ không mang
    thông tin. Trả về NaN để các khâu sau coi là "không có giá trị" thay vì đánh giá
    con số đó. Xem DERIVED_CEILING.
    """
    ceiling = DERIVED_CEILING.get(name)
    if ceiling is None:
        return derived
    bad = derived.notna() & (derived > ceiling)
    if not bad.any():
        return derived
    for idx in df.index[bad]:
        gaps.append({
            "bank_id": df.at[idx, "bank_id"] if "bank_id" in df.columns else None,
            "period": df.at[idx, "period"] if "period" in df.columns else None,
            "metric": name, "reason": "DENOMINATOR_COLLAPSED",
            "message": (f"{name} suy ra từ thành phần = {derived.at[idx]:,.2f}%, vượt "
                        f"trần {ceiling:g}% — mẫu số không còn là số chia có nghĩa "
                        f"nên KHÔNG đánh giá chỉ tiêu này."),
        })
    LOG.info("derive_ratios: bỏ %d giá trị %s suy ra vượt trần %g%%",
             int(bad.sum()), name, ceiling)
    return derived.where(~bad)


def add_trend_features(df: pd.DataFrame, metrics: list[str], window: int = 4) -> pd.DataFrame:
    """Per-bank rolling/trend features for the given metrics (sorted by period_ts)."""
    out = df.sort_values(["bank_id", "period_ts"]).copy()
    g = out.groupby("bank_id", group_keys=False)
    for m in metrics:
        if m not in out.columns:
            continue
        s = out[m]
        roll_mean = g[m].transform(lambda x: x.rolling(window, min_periods=2).mean())
        roll_std = g[m].transform(lambda x: x.rolling(window, min_periods=2).std())
        out[f"{m}__roll_mean"] = roll_mean
        out[f"{m}__roll_std"] = roll_std
        out[f"{m}__roll_z"] = (s - roll_mean) / roll_std.replace(0, np.nan)
        # pandas >= 3.0 bỏ fill_method='pad' (mặc định cũ ở pandas 2.x): pct_change
        # thô trả NaN nếu kỳ liền trước trống. Chỉ tiêu báo cáo theo quý nằm trên
        # lưới tháng chỉ có số ở tháng cuối quý -> mọi cặp kỳ liền kề đều dính NaN
        # và qoq/yoy/accel thành 100% NaN. Lấy giá trị hợp lệ gần nhất (ffill) rồi
        # mới tính biến động: đúng ngữ nghĩa cũ và khớp thiết kế "bậc thang".
        out[f"{m}__qoq"] = g[m].transform(lambda x: x.ffill().pct_change() * 100)
        out[f"{m}__yoy"] = g[m].transform(
            lambda x: x.ffill().pct_change(periods=4) * 100)
        out[f"{m}__accel"] = g[f"{m}__qoq"].transform(lambda x: x.diff())
        cummax = g[m].transform(lambda x: x.cummax())
        out[f"{m}__drawdown"] = (s - cummax) / cummax.replace(0, np.nan) * 100
    return out


def add_systemic_features(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Cross-sectional features computed within each period across all banks."""
    out = df.copy()
    for m in metrics:
        if m not in out.columns:
            continue
        grp = out.groupby("period")[m]
        out[f"{m}__pct_rank"] = grp.transform(lambda x: x.rank(pct=True) * 100)
        median = grp.transform("median")
        std = grp.transform("std").replace(0, np.nan)
        out[f"{m}__dev_sys_median"] = out[m] - median
        out[f"{m}__z_cross"] = (out[m] - median) / std
    return out


# Metrics whose worsening raises systemic stress, with sign (+1 = higher worse).
STRESS_METRICS = {
    "npl_ratio": +1, "group2_ratio": +1, "ldr": +1, "st_funding_for_mlt_loans": +1,
    "car_solo": -1, "car_consolidated": -1, "liquidity_reserve_ratio": -1,
    "avg_liquid_asset_ratio": -1,
    "roa": -1, "solvency_30d_vnd": -1, "solvency_30d_fx": -1,
}


def compute_systemic_stress(df: pd.DataFrame) -> pd.DataFrame:
    """Per-period systemic stress index = mean cross-sectional z of stress metrics,
    oriented so higher = more stress. Returns a period-indexed frame.
    """
    rows = []
    for period, sub in df.groupby("period"):
        ts = sub["period_ts"].iloc[0]
        comps = []
        for m, sign in STRESS_METRICS.items():
            if m not in sub.columns:
                continue
            vals = pd.to_numeric(sub[m], errors="coerce")
            if vals.notna().sum() < 3:
                continue
            z = (vals - vals.mean()) / (vals.std(ddof=0) or np.nan)
            comps.append(sign * z.mean())  # mean across banks of oriented z
        stress = float(np.nanmean(comps)) if comps else np.nan
        rows.append({"period": period, "period_ts": ts, "systemic_stress_index": stress,
                     "n_banks": sub["bank_id"].nunique()})
    res = pd.DataFrame(rows).sort_values("period_ts")
    if not res.empty:
        s = res["systemic_stress_index"]
        res["systemic_stress_pct"] = s.rank(pct=True) * 100
    return res


def build_features(wide: pd.DataFrame, frequency: str = "quarterly") -> pd.DataFrame:
    """Full feature pipeline for a single-frequency wide table."""
    if wide is None or wide.empty:
        return pd.DataFrame()
    cfg = load_config("model_config")
    window = cfg.get("time_series", {}).get("rolling_window", 4)
    df = derive_ratios(wide)
    # Giữ lại trước khi qua add_*/merge — pandas không bảo toàn attrs qua merge.
    ratio_gaps = df.attrs.get("derived_ratio_gaps", pd.DataFrame(columns=GAP_COLUMNS))

    # Candidate analytical metrics = numeric, reasonably populated columns.
    numeric_cols = [c for c in df.columns if c not in ID_COLS
                    and pd.api.types.is_numeric_dtype(df[c])]
    min_ratio = cfg.get("preprocessing", {}).get("min_non_null_ratio", 0.3)
    metrics = [c for c in numeric_cols if df[c].notna().mean() >= min_ratio]

    df = add_trend_features(df, metrics, window=window)
    df = add_systemic_features(df, metrics)

    stress = compute_systemic_stress(df)
    if not stress.empty:
        df = df.merge(stress[["period", "systemic_stress_index", "systemic_stress_pct"]],
                      on="period", how="left")
        thr = cfg.get("time_series", {}).get("high_risk_period", {}).get("systemic_stress_pct", 0.75) * 100
        df["high_risk_period_flag"] = (df["systemic_stress_pct"] >= thr).astype(int)

    df.attrs["base_metrics"] = metrics
    df.attrs["frequency"] = frequency
    df.attrs["derived_ratio_gaps"] = ratio_gaps
    LOG.info("Features built for %s: %d bank-periods, %d base metrics, %d total cols",
             frequency, len(df), len(metrics), df.shape[1])
    return df


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    res = load_all(DATA_ROOT, use_cache=True)
    for freq, w in res.wide.items():
        feats = build_features(w, freq)
        print(f"{freq}: {feats.shape}, base metrics: {len(feats.attrs.get('base_metrics', []))}")
