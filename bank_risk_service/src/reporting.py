"""Report generation: Excel workbook, HTML audit report and CSV exports.

Builds the audit deliverables from an ``AnalysisResult``:
  * Executive summary, top-10 risk banks, CRITICAL legal breaches, ML anomalies,
    risk clusters, high-risk periods, credit / liquidity assessment, fraud/failure
    proxy red-flags, recommended audit focus and a rule appendix.
  * Multi-sheet Excel export and a self-contained HTML report.
  * A standalone CSV of CRITICAL banks with reasons.

Every report carries the disclaimer that ML output supports — but does not replace —
the auditor's professional judgement.
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import pandas as pd

from .utils import DATA_ROOT, EXPORTS_DIR, LOG, REPORTS_DIR, load_config

DISCLAIMER = (
    "Kết quả phân tích là CÔNG CỤ HỖ TRỢ kiểm toán, KHÔNG thay thế kết luận chuyên "
    "môn của kiểm toán viên. Các ngưỡng pháp lý phải được KTV đối chiếu với văn bản "
    "gốc của NHNN. Mô hình ML (Isolation Forest, K-means) đưa ra cảnh báo/xếp hạng "
    "nguy cơ dựa trên dữ liệu, không khẳng định chắc chắn gian lận hoặc đổ vỡ."
)


# --------------------------------------------------------------------------- #
# Report-content builders (frequency-agnostic; operate on an AnalysisResult)
# --------------------------------------------------------------------------- #
def _executive_summary(res) -> dict:
    scores = res.risk_scores
    n_banks = res.features["bank_id"].nunique() if not res.features.empty else 0
    n_periods = res.features["period"].nunique() if not res.features.empty else 0
    crit = 0
    if not scores.empty:
        crit = scores.loc[scores["risk_level"] == "CRITICAL", "bank_id"].nunique()
    n_violations = 0
    if not res.rule_findings.empty:
        n_violations = int((res.rule_findings["finding_type"] == "VIOLATION").sum())
    n_anom = int(res.anomalies["anomaly_label"].sum()) if not res.anomalies.empty else 0
    n_hrp = int(res.high_risk_periods["is_high_risk"].sum()) if not res.high_risk_periods.empty else 0
    ews_alarm = ews_warning = 0
    ews_sys = "—"
    if getattr(res, "ews_latest", None) is not None and not res.ews_latest.empty:
        ews_alarm = int((res.ews_latest["ews_level"] == "ALARM").sum())
        ews_warning = int((res.ews_latest["ews_level"] == "WARNING").sum())
    if getattr(res, "ews_system", None) is not None and not res.ews_system.empty:
        ews_sys = res.ews_system.iloc[-1].get("system_label", "—")
    stress_txt = "—"
    if getattr(res, "stress_system", None) is not None and not res.stress_system.empty:
        sev = res.stress_system[res.stress_system["scenario_id"] == "severe"]
        if not sev.empty:
            r = sev.iloc[0]
            stress_txt = (f"{int(r['n_fail_capital'])} NH thiếu vốn, "
                          f"~{r['total_capital_shortfall']:.0f} tỷ (kịch bản nghiêm trọng)")
    return {
        "Tần suất": res.frequency,
        "Số ngân hàng": n_banks,
        "Số kỳ": n_periods,
        "Ngân hàng mức CRITICAL (kỳ gần nhất)": crit,
        "EWS — trạng thái hệ thống (kỳ gần nhất)": ews_sys,
        "EWS — số NH Báo động / Cảnh báo": f"{ews_alarm} / {ews_warning}",
        "Stress-test (kịch bản nghiêm trọng)": stress_txt,
        "Số vi phạm rule": n_violations,
        "Số bank-period bất thường (ML)": n_anom,
        "Số kỳ rủi ro cao": n_hrp,
        "Số cụm K-means": res.cluster_k,
        "Thời gian chạy (s)": res.runtime_sec,
    }


def _top_risk_banks(res, n: int = 10) -> pd.DataFrame:
    if res.bank_ranking.empty:
        return pd.DataFrame()
    cols = [c for c in ["bank_id", "bank_name", "period", "final_risk_score",
                        "risk_level", "credit_risk_score", "liquidity_risk_score",
                        "fraud_risk_proxy_score", "failure_risk_proxy_score",
                        "cluster_risk_label", "worst_rule_severity"]
            if c in res.bank_ranking.columns]
    return res.bank_ranking[cols].head(n).reset_index(drop=True)


def _critical_legal(res) -> pd.DataFrame:
    rf = res.rule_findings
    if rf.empty:
        return pd.DataFrame()
    crit = rf[(rf["severity"] == "CRITICAL") & (rf["finding_type"] == "VIOLATION")]
    cols = [c for c in ["bank_id", "bank_name", "period", "rule_name", "metric",
                        "metric_value", "operator", "threshold", "legal_source",
                        "article_reference", "audit_recommendation"]
            if c in crit.columns]
    return crit[cols].sort_values(["bank_id", "period"]).reset_index(drop=True)


def _top_anomalies(res, n: int = 20) -> pd.DataFrame:
    an = res.anomalies
    if an.empty:
        return pd.DataFrame()
    return (an.sort_values("anomaly_score", ascending=False)
            [["bank_id", "period", "anomaly_score", "anomaly_label", "top_features"]]
            .head(n).reset_index(drop=True))


def _cluster_table(res) -> pd.DataFrame:
    if res.cluster_profiles.empty:
        return pd.DataFrame()
    keep = [c for c in ["cluster_id", "n_banks", "cluster_risk_score",
                        "cluster_risk_label"] if c in res.cluster_profiles.columns]
    return res.cluster_profiles[keep].reset_index(drop=True)


def _high_risk_periods(res) -> pd.DataFrame:
    hrp = res.high_risk_periods
    if hrp.empty:
        return pd.DataFrame()
    return hrp[hrp["is_high_risk"]][
        ["period", "period_risk_score", "risk_domains", "reason",
         "recommended_audit_focus"]].reset_index(drop=True)


def _domain_assessment(res, domain_score_col: str, label: str, n: int = 10) -> pd.DataFrame:
    scores = res.bank_ranking
    if scores.empty or domain_score_col not in scores.columns:
        return pd.DataFrame()
    cols = ["bank_id", "period", domain_score_col]
    return (scores.sort_values(domain_score_col, ascending=False)[cols]
            .head(n).reset_index(drop=True))


def _critical_banks_with_reasons(res) -> pd.DataFrame:
    """Standalone CRITICAL-bank list with the reason for the flag."""
    scores = res.risk_scores
    if scores.empty:
        return pd.DataFrame()
    crit = scores[scores["risk_level"] == "CRITICAL"].copy()
    if crit.empty:
        return pd.DataFrame()
    rf = res.rule_findings
    reasons = []
    for _, r in crit.iterrows():
        bits = []
        if rf is not None and not rf.empty:
            sub = rf[(rf["bank_id"] == r["bank_id"]) & (rf["period"] == r["period"]) &
                     (rf["severity"] == "CRITICAL") & (rf["finding_type"] == "VIOLATION")]
            for _, v in sub.iterrows():
                bits.append(f"{v['rule_name']} ({v['metric']}={v['metric_value']})")
        if not bits and pd.notna(r.get("anomaly_score")) and r.get("anomaly_label") == 1:
            bits.append(f"Bất thường ML (score {r['anomaly_score']})")
        reasons.append("; ".join(bits) if bits else "Điểm rủi ro tổng hợp cao")
    crit = crit[["bank_id", "bank_name", "period", "final_risk_score", "risk_level"]].copy()
    crit["reason"] = reasons
    return crit.sort_values("final_risk_score", ascending=False).reset_index(drop=True)


def _ews_latest(res, n: int = 25) -> pd.DataFrame:
    if getattr(res, "ews_latest", None) is None or res.ews_latest.empty:
        return pd.DataFrame()
    cols = [c for c in ["bank_id", "bank_name", "period", "ews_score", "ews_level",
                        "ews_label", "score_delta", "n_breached",
                        "projected_periods_to_breach", "projected_breach_metric",
                        "risk_domains", "drivers"] if c in res.ews_latest.columns]
    return res.ews_latest[cols].head(n).reset_index(drop=True)


def _ews_system(res) -> pd.DataFrame:
    if getattr(res, "ews_system", None) is None or res.ews_system.empty:
        return pd.DataFrame()
    cols = [c for c in ["period", "mean_ews", "share_warning_plus", "n_warning_plus",
                        "n_alarm", "n_warning", "system_level", "system_label"]
            if c in res.ews_system.columns]
    return res.ews_system[cols].reset_index(drop=True)


def _ews_emerging(res) -> pd.DataFrame:
    if getattr(res, "ews_emerging", None) is None or res.ews_emerging.empty:
        return pd.DataFrame()
    return res.ews_emerging.reset_index(drop=True)


def _stress_system(res) -> pd.DataFrame:
    if getattr(res, "stress_system", None) is None or res.stress_system.empty:
        return pd.DataFrame()
    cols = [c for c in ["scenario_name", "n_fail_capital", "total_capital_shortfall",
                        "min_stressed_car", "avg_stressed_car", "assets_share_failing",
                        "n_fail_liquidity", "total_liquidity_gap"]
            if c in res.stress_system.columns]
    return res.stress_system[cols].reset_index(drop=True)


def _stress_capital(res, scenario_id: str = "severe", n: int = 30) -> pd.DataFrame:
    if getattr(res, "stress_results", None) is None or res.stress_results.empty:
        return pd.DataFrame()
    df = res.stress_results
    snap = getattr(res, "stress_snapshot", None)
    if snap is not None and "period" in df.columns:
        df = df[df["period"] == snap]
    sub = df[(df["scenario_id"] == scenario_id) & (df.get("capital_status") == "OK")]
    if sub.empty:
        sub = df[df.get("capital_status") == "OK"]
    # Ở tần suất không có dữ liệu CAR (vd yearly), stress engine không sinh cột
    # 'stressed_car' -> trả bảng rỗng thay vì lỗi.
    if sub.empty or "stressed_car" not in sub.columns:
        return pd.DataFrame()
    cols = [c for c in ["bank_id", "scenario_name", "baseline_car", "stressed_car",
                        "car_delta", "capital_shortfall", "passes_capital"]
            if c in sub.columns]
    return sub.sort_values("stressed_car")[cols].head(n).reset_index(drop=True)


def _stress_breaking(res, n: int = 30) -> pd.DataFrame:
    if getattr(res, "stress_breaking", None) is None or res.stress_breaking.empty:
        return pd.DataFrame()
    df = res.stress_breaking
    snap = getattr(res, "stress_snapshot", None)
    if snap is not None and "period" in df.columns:
        df = df[df["period"] == snap]
    df = df[df["breaking_npl_pp"].notna()].sort_values("breaking_npl_pp")
    return df.head(n).reset_index(drop=True)


def _rule_appendix() -> pd.DataFrame:
    rules = load_config("regulatory_rules").get("rules", [])
    rows = [{
        "rule_id": r.get("rule_id"), "rule_name": r.get("rule_name"),
        "metric": r.get("metric"), "operator": r.get("operator"),
        "threshold": r.get("threshold"), "severity": r.get("severity"),
        "status": r.get("status"), "risk_domain": r.get("risk_domain"),
        "legal_source": r.get("legal_source"),
        "article_reference": r.get("article_reference"),
        "formula": r.get("formula"),
    } for r in rules]
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Excel export
# --------------------------------------------------------------------------- #
def export_excel(res, path: Path | str | None = None) -> str:
    """Write a multi-sheet Excel workbook with all report sections."""
    path = Path(path) if path else EXPORTS_DIR / f"bank_risk_report_{res.frequency}.xlsx"
    sheets = {
        "Tong_quan": pd.DataFrame(list(_executive_summary(res).items()),
                                  columns=["Chỉ tiêu", "Giá trị"]),
        "Top_rui_ro": _top_risk_banks(res, 20),
        "EWS_canh_bao_som": _ews_latest(res, 35),
        "EWS_he_thong": _ews_system(res),
        "EWS_rui_ro_moi_noi": _ews_emerging(res),
        "StressTest_he_thong": _stress_system(res),
        "StressTest_von_severe": _stress_capital(res, "severe", 35),
        "StressTest_diem_gay": _stress_breaking(res, 35),
        "CRITICAL_phap_ly": _critical_legal(res),
        "CRITICAL_co_ly_do": _critical_banks_with_reasons(res),
        "Bat_thuong_ML": _top_anomalies(res, 50),
        "Phan_cum": _cluster_table(res),
        "Ky_rui_ro_cao": _high_risk_periods(res),
        "Tin_dung": _domain_assessment(res, "credit_risk_score", "Credit"),
        "Thanh_khoan": _domain_assessment(res, "liquidity_risk_score", "Liquidity"),
        "Fraud_proxy": _domain_assessment(res, "fraud_risk_proxy_score", "Fraud"),
        "Failure_proxy": _domain_assessment(res, "failure_risk_proxy_score", "Failure"),
        "Diem_rui_ro_day_du": res.risk_scores,
        "Validation": res.validation,
        "Phu_luc_rule": _rule_appendix(),
    }
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        disclaimer_df = pd.DataFrame({"Lưu ý": [DISCLAIMER]})
        disclaimer_df.to_excel(writer, sheet_name="Luu_y", index=False)
        for name, df in sheets.items():
            (df if df is not None and not df.empty
             else pd.DataFrame({"info": ["(không có dữ liệu)"]})).to_excel(
                writer, sheet_name=name[:31], index=False)
    LOG.info("Excel report -> %s", path)
    return str(path)


# --------------------------------------------------------------------------- #
# HTML export
# --------------------------------------------------------------------------- #
def _df_to_html(df: pd.DataFrame, max_rows: int = 100) -> str:
    if df is None or df.empty:
        return "<p><em>(không có dữ liệu)</em></p>"
    return df.head(max_rows).to_html(index=False, border=0, escape=True,
                                     classes="tbl", na_rep="")


def export_html(res, path: Path | str | None = None) -> str:
    """Write a self-contained HTML audit report."""
    path = Path(path) if path else REPORTS_DIR / f"bank_risk_report_{res.frequency}.html"
    summary = _executive_summary(res)
    summary_rows = "".join(
        f"<tr><td>{html.escape(str(k))}</td><td><b>{html.escape(str(v))}</b></td></tr>"
        for k, v in summary.items())

    sections = [
        ("1. Tóm tắt điều hành (Executive Summary)",
         f"<table class='tbl'>{summary_rows}</table>"),
        ("2. Top 10 ngân hàng rủi ro cao", _df_to_html(_top_risk_banks(res, 10))),
        ("2b. Cảnh báo sớm (EWS) — ngân hàng mức cao nhất",
         _df_to_html(_ews_latest(res, 15)) +
         "<h3 style='font-size:13px;margin-top:12px'>Rủi ro mới nổi (escalating)</h3>" +
         _df_to_html(_ews_emerging(res))),
        ("2c. Stress-test — sức chịu đựng vốn & thanh khoản",
         _df_to_html(_stress_system(res)) +
         "<h3 style='font-size:13px;margin-top:12px'>Kịch bản nghiêm trọng — CAR sau sốc (yếu nhất)</h3>" +
         _df_to_html(_stress_capital(res, "severe", 12)) +
         "<h3 style='font-size:13px;margin-top:12px'>Reverse stress — NPL (điểm %) để CAR chạm 8%</h3>" +
         _df_to_html(_stress_breaking(res, 12))),
        ("3. Vi phạm pháp lý CRITICAL", _df_to_html(_critical_legal(res))),
        ("4. Danh sách CRITICAL kèm lý do", _df_to_html(_critical_banks_with_reasons(res))),
        ("5. Bất thường ML (Isolation Forest)", _df_to_html(_top_anomalies(res, 20))),
        ("6. Phân cụm rủi ro (K-means)", _df_to_html(_cluster_table(res))),
        ("7. Giai đoạn rủi ro cao", _df_to_html(_high_risk_periods(res))),
        ("8. Rủi ro tín dụng (top)", _df_to_html(_domain_assessment(res, "credit_risk_score", "Credit"))),
        ("9. Rủi ro thanh khoản (top)", _df_to_html(_domain_assessment(res, "liquidity_risk_score", "Liquidity"))),
        ("10. Dấu hiệu gian lận / đổ vỡ (proxy)",
         _df_to_html(_domain_assessment(res, "fraud_risk_proxy_score", "Fraud")) +
         _df_to_html(_domain_assessment(res, "failure_risk_proxy_score", "Failure"))),
        ("11. Phụ lục rule & công thức", _df_to_html(_rule_appendix(), max_rows=200)),
    ]
    body = "".join(f"<section><h2>{html.escape(t)}</h2>{c}</section>" for t, c in sections)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Báo cáo phân tích rủi ro hệ thống ngân hàng — {html.escape(res.frequency)}</title>
<style>
 body{{font-family:'Segoe UI',Arial,sans-serif;margin:24px;color:#1a1a1a;line-height:1.5}}
 h1{{color:#0b3d63}} h2{{color:#0b3d63;border-bottom:2px solid #e0e0e0;padding-bottom:4px;margin-top:28px}}
 .tbl{{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}}
 .tbl td,.tbl th{{border:1px solid #ddd;padding:5px 8px;text-align:left}}
 .tbl th{{background:#0b3d63;color:#fff}} .tbl tr:nth-child(even){{background:#f6f9fc}}
 .warn{{background:#fff4e5;border-left:5px solid #ff9800;padding:12px;margin:16px 0;border-radius:4px}}
 footer{{margin-top:32px;font-size:12px;color:#666}}
</style></head><body>
<h1>Báo cáo phân tích & đánh giá rủi ro hệ thống ngân hàng</h1>
<p>Phục vụ kiểm toán NHNN · Tần suất: <b>{html.escape(res.frequency)}</b> · Lập lúc: {now}</p>
<div class="warn"><b>⚠ Lưu ý:</b> {html.escape(DISCLAIMER)}</div>
{body}
<footer>Sinh tự động bởi Bank System Risk Analysis Toolkit. Mọi ngưỡng pháp lý cần KTV xác nhận với văn bản gốc.</footer>
</body></html>"""
    Path(path).write_text(doc, encoding="utf-8")
    LOG.info("HTML report -> %s", path)
    return str(path)


def export_critical_csv(res, path: Path | str | None = None) -> str:
    path = Path(path) if path else EXPORTS_DIR / f"critical_banks_{res.frequency}.csv"
    df = _critical_banks_with_reasons(res)
    (df if not df.empty else pd.DataFrame({"info": ["Không có ngân hàng CRITICAL"]})).to_csv(
        path, index=False, encoding="utf-8-sig")
    LOG.info("CRITICAL CSV -> %s", path)
    return str(path)


def generate_all_reports(res) -> dict:
    """Produce Excel + HTML + CRITICAL CSV and return their paths."""
    return {
        "excel": export_excel(res),
        "html": export_html(res),
        "critical_csv": export_critical_csv(res),
    }


if __name__ == "__main__":
    from .pipeline import run_pipeline
    r = run_pipeline(DATA_ROOT, "quarterly")
    paths = generate_all_reports(r)
    for k, v in paths.items():
        print(f"{k}: {v}")
