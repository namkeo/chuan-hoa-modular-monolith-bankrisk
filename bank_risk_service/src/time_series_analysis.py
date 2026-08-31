"""Time-series analysis and high-risk-period identification.

Two views:
  * Per-bank metric series with rolling z-score / drawdown / volatility (used by the
    Time Series dashboard page and for trend risk).
  * High-risk periods, computed for the whole system AND per bank, by combining:
      - count of CRITICAL / HIGH rule findings in the period,
      - anomaly rate in the period,
      - systemic stress index,
      - sharp moves of NPL / group-2 / liquidity / profit / CAR / LDR,
      - breadth (many banks deteriorating in the same period).

Returns audit-oriented tables: period, affected_banks, risk_domains, reason,
recommended_audit_focus.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import DATA_ROOT, LOG, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]

# Metrics whose sharp adverse move marks period stress (sign: +1 = up is worse).
WATCH_METRICS = {
    "npl_ratio": +1, "group2_ratio": +1, "ldr": +1, "st_funding_for_mlt_loans": +1,
    "car_solo": -1, "car_consolidated": -1, "liquidity_reserve_ratio": -1,
    "profit_before_tax": -1, "roa": -1,
}

DOMAIN_BY_METRIC = {
    "npl_ratio": "credit", "group2_ratio": "credit", "llr_coverage": "credit",
    "credit_growth_yoy": "credit", "ldr": "liquidity",
    "st_funding_for_mlt_loans": "liquidity", "liquidity_reserve_ratio": "liquidity",
    "solvency_30d_vnd": "liquidity", "solvency_30d_fx": "liquidity", "car_solo": "capital", "car_consolidated": "capital",
    "roa": "profitability", "roe": "profitability", "profit_before_tax": "profitability",
}


def metric_series(features: pd.DataFrame, bank_id: str, metric: str,
                  window: int = 4) -> pd.DataFrame:
    """Return a tidy series for one bank/metric with rolling stats for charting."""
    if metric not in features.columns:
        return pd.DataFrame()
    sub = (features[features["bank_id"] == bank_id]
           .sort_values("period_ts")[["period", "period_ts", metric]].copy())
    if sub.empty:
        return sub
    s = pd.to_numeric(sub[metric], errors="coerce")
    sub["value"] = s
    sub["roll_mean"] = s.rolling(window, min_periods=2).mean()
    sub["roll_std"] = s.rolling(window, min_periods=2).std()
    sub["roll_z"] = (s - sub["roll_mean"]) / sub["roll_std"].replace(0, np.nan)
    cummax = s.cummax()
    sub["drawdown"] = (s - cummax) / cummax.replace(0, np.nan) * 100
    sub["metric"] = metric
    return sub


def _period_breadth(features: pd.DataFrame) -> pd.DataFrame:
    """Per period: share of banks whose key stress metrics worsened vs prior period."""
    f = features.sort_values(["bank_id", "period_ts"]).copy()
    worse = pd.Series(0.0, index=f.index)
    n = pd.Series(0.0, index=f.index)
    for m, sign in WATCH_METRICS.items():
        if m not in f.columns:
            continue
        d = f.groupby("bank_id")[m].diff() * sign  # >0 => worse
        worse += (d > 0).astype(float)
        n += d.notna().astype(float)
    f["worsen_share"] = (worse / n.replace(0, np.nan)).fillna(0.0)
    return (f.groupby(["period", "period_ts"], as_index=False)
            .agg(mean_worsen_share=("worsen_share", "mean"),
                 n_banks=("bank_id", "nunique")))


def identify_high_risk_periods(
    features: pd.DataFrame,
    rule_findings: pd.DataFrame | None,
    anomaly_table: pd.DataFrame | None,
    systemic_stress: pd.DataFrame | None,
    cfg: dict | None = None,
) -> pd.DataFrame:
    """System-level high-risk periods with reasons and audit focus."""
    if features is None or features.empty:
        return pd.DataFrame()
    cfg = cfg or load_config("model_config")
    hp = cfg.get("time_series", {}).get("high_risk_period", {})
    min_anom = hp.get("min_anomaly_rate", 0.20)
    min_crit_banks = hp.get("min_critical_banks", 2)
    stress_pct_thr = hp.get("systemic_stress_pct", 0.75) * 100

    periods = features[["period", "period_ts"]].drop_duplicates().sort_values("period_ts")
    breadth = _period_breadth(features).set_index("period")

    # Rule pressure per period.
    crit_banks = {}
    high_banks = {}
    domains_by_period: dict[str, set] = {}
    if rule_findings is not None and not rule_findings.empty:
        rf = rule_findings.dropna(subset=["period"])
        for period, sub in rf.groupby("period"):
            crit_banks[period] = sub.loc[sub["severity"] == "CRITICAL", "bank_id"].nunique()
            high_banks[period] = sub.loc[sub["severity"] == "HIGH", "bank_id"].nunique()
            domains_by_period[period] = set(sub.loc[
                sub["severity"].isin(["CRITICAL", "HIGH"]), "risk_domain"].dropna())

    # Anomaly rate per period.
    anom_rate = {}
    if anomaly_table is not None and not anomaly_table.empty:
        for period, sub in anomaly_table.groupby("period"):
            anom_rate[period] = float(sub["anomaly_label"].mean())

    stress_map = {}
    if systemic_stress is not None and not systemic_stress.empty:
        stress_map = systemic_stress.set_index("period")["systemic_stress_pct"].to_dict()

    rows = []
    for _, pr in periods.iterrows():
        period = pr["period"]
        nc = crit_banks.get(period, 0)
        nh = high_banks.get(period, 0)
        ar = anom_rate.get(period, np.nan)
        sp = stress_map.get(period, np.nan)
        bw = breadth.loc[period, "mean_worsen_share"] if period in breadth.index else np.nan
        nb = int(breadth.loc[period, "n_banks"]) if period in breadth.index else 0

        reasons = []
        score = 0.0
        if nc >= min_crit_banks:
            reasons.append(f"{nc} ngân hàng vi phạm CRITICAL")
            score += 35
        elif nc > 0:
            reasons.append(f"{nc} ngân hàng vi phạm CRITICAL")
            score += 20
        if nh > 0:
            reasons.append(f"{nh} ngân hàng cảnh báo HIGH")
            score += min(15, nh * 3)
        if pd.notna(ar) and ar >= min_anom:
            reasons.append(f"tỷ lệ bất thường {ar*100:.0f}%")
            score += 20
        if pd.notna(sp) and sp >= stress_pct_thr:
            reasons.append(f"chỉ số căng thẳng hệ thống ở bách phân vị {sp:.0f}")
            score += 20
        if pd.notna(bw) and bw >= 0.5:
            reasons.append(f"{bw*100:.0f}% ngân hàng xấu đi so với kỳ trước")
            score += 15

        domains = sorted(domains_by_period.get(period, set()))
        is_high = score >= 35 or (pd.notna(sp) and sp >= stress_pct_thr and pd.notna(ar) and ar >= min_anom)
        rows.append({
            "period": period, "period_ts": pr["period_ts"],
            "period_risk_score": round(min(score, 100), 1),
            "is_high_risk": bool(is_high),
            "n_critical_banks": nc, "n_high_banks": nh,
            "anomaly_rate": round(ar * 100, 1) if pd.notna(ar) else None,
            "systemic_stress_pct": round(sp, 1) if pd.notna(sp) else None,
            "worsen_share": round(bw * 100, 1) if pd.notna(bw) else None,
            "n_banks": nb,
            "risk_domains": ", ".join(domains) if domains else "",
            "reason": "; ".join(reasons) if reasons else "không có dấu hiệu nổi bật",
            "recommended_audit_focus": _audit_focus(domains, reasons),
        })
    out = pd.DataFrame(rows).sort_values("period_ts").reset_index(drop=True)
    LOG.info("High-risk periods: %d/%d flagged", out["is_high_risk"].sum(), len(out))
    return out


def high_risk_periods_by_bank(
    features: pd.DataFrame,
    rule_findings: pd.DataFrame | None,
    anomaly_table: pd.DataFrame | None,
) -> pd.DataFrame:
    """Per-bank high-risk periods: which periods each bank looked worst."""
    if features is None or features.empty:
        return pd.DataFrame()
    rows = []
    rf = (rule_findings.dropna(subset=["period"])
          if rule_findings is not None and not rule_findings.empty else pd.DataFrame())
    an = anomaly_table if anomaly_table is not None else pd.DataFrame()

    for (bid, period), _ in features.groupby(["bank_id", "period"]):
        nc = nh = 0
        domains = set()
        if not rf.empty:
            sub = rf[(rf["bank_id"] == bid) & (rf["period"] == period)]
            nc = int((sub["severity"] == "CRITICAL").sum())
            nh = int((sub["severity"] == "HIGH").sum())
            domains = set(sub.loc[sub["severity"].isin(["CRITICAL", "HIGH"]),
                                  "risk_domain"].dropna())
        anom = 0
        ascore = np.nan
        if not an.empty:
            a = an[(an["bank_id"] == bid) & (an["period"] == period)]
            if not a.empty:
                anom = int(a["anomaly_label"].iloc[0])
                ascore = float(a["anomaly_score"].iloc[0])
        if nc > 0 or nh > 1 or anom == 1:
            rows.append({
                "bank_id": bid, "period": period,
                "n_critical": nc, "n_high": nh,
                "is_anomaly": anom, "anomaly_score": round(ascore, 1) if pd.notna(ascore) else None,
                "risk_domains": ", ".join(sorted(domains)),
            })
    return pd.DataFrame(rows)


def _audit_focus(domains: list[str], reasons: list[str]) -> str:
    focus = []
    if "credit" in domains:
        focus.append("rà soát phân loại nợ, dự phòng, nợ tái cơ cấu/VAMC")
    if "liquidity" in domains:
        focus.append("kiểm tra LDR, tỷ lệ vốn ngắn hạn cho vay TDH, dự trữ thanh khoản")
    if "capital" in domains:
        focus.append("đối chiếu vốn tự có, RWA, kế hoạch tăng vốn")
    if "profitability" in domains:
        focus.append("phân tích cơ cấu thu nhập và chi phí dự phòng")
    if not focus:
        focus.append("rà soát các ngân hàng có bất thường ML và biến động mạnh trong kỳ")
    return "; ".join(focus)


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    from .feature_engineering import build_features, compute_systemic_stress
    from .rule_engine import evaluate_rules
    from .anomaly_detection import run_isolation_forest
    res = load_all(DATA_ROOT, use_cache=True)
    feats = build_features(res.wide["quarterly"], "quarterly")
    rf = evaluate_rules(feats)
    an = run_isolation_forest(feats, feats.attrs["base_metrics"])
    ss = compute_systemic_stress(feats)
    hrp = identify_high_risk_periods(feats, rf, an.table, ss)
    print(hrp[["period", "period_risk_score", "is_high_risk", "reason"]].tail(12).to_string())
