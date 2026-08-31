"""Expert rule-based system: evaluate SBV regulatory rules per bank-period-metric.

Reads config/regulatory_rules.yaml and applies each rule to the wide feature table.

Hai loại rule:

1. Rule ngưỡng phẳng — một `threshold` áp cho mọi TCTD. Operators: <, <=, >, >=,
   ==, !=, between, outside_range, missing, increasing_fast, decreasing_fast.
   Rule "fires" khi chỉ tiêu VI PHẠM giới hạn.

2. Rule ngưỡng theo loại hình (`tiers_by_type`) — ngưỡng giám sát của NHNN theo
   QĐ 682/QĐ-TTGSNH4 và QĐ 618/QĐ-TTGSNH3, KHÁC NHAU theo loại hình TCTD
   (config/institution_types.yaml). Mỗi chỉ tiêu có 3 bậc:
       Ngưỡng 3 -> VIOLATION / CRITICAL   (vi phạm tỷ lệ an toàn)
       Ngưỡng 2 -> WARNING   / HIGH       (nguy cơ dẫn tới vi phạm)
       Ngưỡng 1 -> WATCH     / MEDIUM     (tăng cường theo dõi)
   Mỗi bank-period chỉ sinh TỐI ĐA MỘT finding cho mỗi rule (các bậc loại trừ
   nhau), nên số liệu đếm vi phạm không bị trùng.

Severity CRITICAL dành cho vi phạm quy định pháp lý bắt buộc; thiếu dữ liệu cho
rule pháp lý quan trọng sinh DATA_GAP. Đơn vị thuộc diện kiểm soát đặc biệt /
can thiệp sớm không được so ngưỡng (QĐ 682, Phụ lục 3 mục 3.2) -> sinh finding
SPECIAL_CONTROL để KTV biết vì sao không có cờ vi phạm.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import LOG, load_config

SEVERITY_ORDER = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
# A change of more than this %/period counts as increasing/decreasing fast.
FAST_CHANGE_PCT = 25.0

# Bậc ngưỡng -> (finding_type, severity). Chỉ Ngưỡng 3 là VIOLATION, nên chỉ
# Ngưỡng 3 kích hoạt ép CRITICAL ở risk_scoring (xem _mandatory_critical_rule_ids).
TIER_MEANING = {
    "n3": ("VIOLATION", "CRITICAL"),
    "n2": ("WARNING", "HIGH"),
    "n1": ("WATCH", "MEDIUM"),
}
TIER_ACTION = {
    "n3": "Vượt Ngưỡng 3 — vi phạm tỷ lệ bảo đảm an toàn: thực hiện các biện pháp "
          "xử lý trong giám sát ngân hàng theo quy định pháp luật.",
    "n2": "Trong khoảng Ngưỡng 2–Ngưỡng 3 — nguy cơ dẫn tới vi phạm tuân thủ: tìm "
          "hiểu nguyên nhân, xem xét đưa ra khuyến nghị, cảnh báo phù hợp.",
    "n1": "Trong khoảng Ngưỡng 1–Ngưỡng 2: tăng cường theo dõi chỉ tiêu, tìm hiểu "
          "nguyên nhân biến động.",
}


def _as_float(x):
    try:
        v = float(x)
        return v if v == v else None  # filter NaN
    except (TypeError, ValueError):
        return None


def _evaluate(operator: str, value, threshold) -> bool:
    """Return True when the rule FIRES (i.e. the metric violates the limit)."""
    v = _as_float(value)
    if operator == "missing":
        return v is None
    if v is None:
        return False
    if operator == "<":
        return v < threshold
    if operator == "<=":
        return v <= threshold
    if operator == ">":
        return v > threshold
    if operator == ">=":
        return v >= threshold
    if operator == "==":
        return v == threshold
    if operator == "!=":
        return v != threshold
    if operator == "between":          # violation = inside [lo, hi]
        lo, hi = threshold
        return lo <= v <= hi
    if operator == "outside_range":    # violation = outside [lo, hi]
        lo, hi = threshold
        return v < lo or v > hi
    LOG.warning("Unknown operator '%s' — rule skipped", operator)
    return False


# --------------------------------------------------------------------------- #
# Ngưỡng giám sát theo loại hình TCTD (QĐ 682 / QĐ 618)
# --------------------------------------------------------------------------- #
def load_institution_types(cfg: dict | None = None) -> tuple[dict, dict]:
    """Trả về (bank_id -> loại hình, bank_id -> lý do không áp ngưỡng).

    Đơn vị thuộc `special_control` không được so ngưỡng theo QĐ 682 Phụ lục 3.
    """
    cfg = cfg or load_config("institution_types")
    types = {bid: (v or {}).get("type") for bid, v in (cfg.get("banks") or {}).items()}
    excluded = {e["bank_id"]: e.get("reason", "Không áp ngưỡng theo QĐ 682 Phụ lục 3")
                for e in (cfg.get("special_control") or []) if e.get("bank_id")}
    return types, excluded


def _tier_for(value, tiers: dict, direction: str) -> str | None:
    """Bậc ngưỡng mà `value` rơi vào: 'n3' | 'n2' | 'n1' | None (bình thường).

    Các bậc LOẠI TRỪ nhau -> mỗi bank-period chỉ sinh một finding cho mỗi rule.
    Theo QĐ 682 Phụ lục 3 mục 3.1:
      lower_riskier  (càng nhỏ càng rủi ro): x < N3 vi phạm; N3<=x<N2 cảnh báo;
                                             N2<=x<N1 theo dõi; x>=N1 bình thường.
      higher_riskier (càng lớn càng rủi ro): x > N3 vi phạm; N2<x<=N3 cảnh báo;
                                             N1<x<=N2 theo dõi; x<=N1 bình thường.
    """
    v = _as_float(value)
    if v is None:
        return None
    n1, n2, n3 = (_as_float(tiers.get(k)) for k in ("n1", "n2", "n3"))
    if direction == "lower_riskier":
        if n3 is not None and v < n3:
            return "n3"
        if n2 is not None and v < n2:
            return "n2"
        if n1 is not None and v < n1:
            return "n1"
        return None
    if direction == "higher_riskier":
        if n3 is not None and v > n3:
            return "n3"
        if n2 is not None and v > n2:
            return "n2"
        if n1 is not None and v > n1:
            return "n1"
        return None
    LOG.warning("Unknown direction '%s' — rule skipped", direction)
    return None


def _check_tier_order(rule: dict) -> None:
    """Cảnh báo khi ngưỡng khai báo sai thứ tự (N1/N2 bị đảo).

    Với lower_riskier phải có N1>=N2>=N3; higher_riskier phải có N1<=N2<=N3. Bậc
    đảo nhau làm các khoảng chồng lấn -> bậc giữa không bao giờ kích hoạt. Bản
    tổng hợp .docx của QĐ 682 từng đảo cột Ngưỡng 1/Ngưỡng 2 ở 4 ô, nên kiểm tra
    này giữ cho lỗi kiểu đó không lọt vào im lặng.
    """
    direction = rule.get("direction")
    for itype, tiers in (rule.get("tiers_by_type") or {}).items():
        vals = [_as_float(tiers.get(k)) for k in ("n1", "n2", "n3")]
        if any(v is None for v in vals):
            continue
        n1, n2, n3 = vals
        ok = (n1 >= n2 >= n3) if direction == "lower_riskier" else (n1 <= n2 <= n3)
        if not ok:
            LOG.warning(
                "Rule %s / %s: ngưỡng SAI THỨ TỰ (N1=%s, N2=%s, N3=%s) với "
                "direction=%s — bậc giữa sẽ không bao giờ kích hoạt. Kiểm tra lại "
                "config/regulatory_rules.yaml so với văn bản gốc.",
                rule.get("rule_id"), itype, n1, n2, n3, direction)


def _trend_fires(operator: str, series: pd.Series, idx, threshold) -> bool:
    """Handle increasing_fast / decreasing_fast using the per-bank series."""
    pos = series.index.get_loc(idx)
    if pos == 0:
        return False
    prev = _as_float(series.iloc[pos - 1])
    cur = _as_float(series.iloc[pos])
    if prev in (None, 0) or cur is None:
        return False
    change = (cur - prev) / abs(prev) * 100
    thr = threshold if isinstance(threshold, (int, float)) else FAST_CHANGE_PCT
    if operator == "increasing_fast":
        return change >= thr
    if operator == "decreasing_fast":
        return change <= -thr
    return False


def _unclassified_rows(feat: pd.DataFrame, inst_types: dict, excluded: dict,
                       tiered_rules: list[dict]) -> list[dict]:
    """Finding cho đơn vị CHƯA được phân loại loại hình TCTD.

    Không phân loại được => không biết áp ngưỡng QĐ 682/618 nào => toàn bộ kiểm
    tra tuân thủ theo ngưỡng bị bỏ qua. Phải nói rõ thay vì im lặng, nếu không
    một file mới thêm vào data_all mà quên khai báo loại hình sẽ trông như
    "không vi phạm gì".
    """
    if not tiered_rules:
        return []
    unknown = sorted({b for b in feat["bank_id"].unique()
                      if b not in inst_types and b not in excluded})
    if not unknown:
        return []
    LOG.warning("%d đơn vị CHƯA phân loại loại hình TCTD -> KHÔNG áp được ngưỡng "
                "giám sát QĐ 682/618 (%d rule bị bỏ qua với các đơn vị này): %s. "
                "Bổ sung vào config/institution_types.yaml.",
                len(unknown), len(tiered_rules), ", ".join(unknown))
    sub = feat[feat["bank_id"].isin(unknown)]
    return [{
        "bank_id": row["bank_id"], "bank_name": row["bank_name"],
        "period": row["period"], "period_ts": row["period_ts"],
        "rule_id": "INSTITUTION_TYPE_UNKNOWN",
        "rule_name": "Chưa phân loại loại hình TCTD — không áp được ngưỡng giám sát",
        "metric": None, "metric_value": None, "operator": None, "threshold": None,
        "severity": "DATA_GAP", "status": "ACTIVE", "risk_domain": "governance",
        "legal_source": "QĐ 682/QĐ-TTGSNH4; QĐ 618/QĐ-TTGSNH3",
        "article_reference": "—",
        "finding_type": "DATA_GAP",
        "description": (f"Đơn vị {row['bank_id']} chưa khai báo loại hình trong "
                        f"config/institution_types.yaml nên KHÔNG kiểm tra được "
                        f"{len(tiered_rules)} ngưỡng giám sát theo loại hình."),
        "audit_recommendation": "Bổ sung loại hình TCTD của đơn vị vào config/institution_types.yaml rồi chạy lại.",
    } for _, row in sub.iterrows()]


def evaluate_rules(features: pd.DataFrame, rules_cfg: dict | None = None,
                   inst_cfg: dict | None = None) -> pd.DataFrame:
    """Apply all rules to every bank-period. Returns a long findings table.

    Columns: bank_id, bank_name, period, period_ts, rule_id, rule_name, metric,
    metric_value, operator, threshold, severity, status, risk_domain, legal_source,
    article_reference, finding_type ('VIOLATION' | 'DATA_GAP'), description,
    audit_recommendation.
    """
    if features is None or features.empty:
        return pd.DataFrame()
    rules_cfg = rules_cfg or load_config("regulatory_rules")
    rules = rules_cfg.get("rules", [])
    findings = []

    inst_types, excluded = load_institution_types(inst_cfg)
    feat = features.sort_values(["bank_id", "period_ts"])
    tiered = [r for r in rules if r.get("tiers_by_type")]

    # Đơn vị kiểm soát đặc biệt: không so ngưỡng, nhưng phải nói rõ lý do.
    findings.extend(_special_control_rows(feat, excluded))
    # Đơn vị chưa phân loại: cũng không so được ngưỡng -> phải nói rõ, không im lặng.
    findings.extend(_unclassified_rows(feat, inst_types, excluded, tiered))

    for rule in rules:
        metric = rule.get("metric")
        operator = rule.get("operator")
        threshold = rule.get("threshold")
        severity = rule.get("severity", "MEDIUM")
        status = rule.get("status", "ACTIVE")
        is_legal_critical = severity == "CRITICAL"

        if rule.get("tiers_by_type"):
            findings.extend(_evaluate_tiered_rule(rule, feat, inst_types, excluded))
            continue

        if metric not in feat.columns:
            # Important legal rule but the metric is entirely absent -> system-wide DATA_GAP.
            if is_legal_critical:
                findings.append(_data_gap_row(rule, bank_id=None, bank_name=None,
                                              period=None, period_ts=None,
                                              note="Chỉ tiêu không có trong dữ liệu"))
            continue

        trend_op = operator in ("increasing_fast", "decreasing_fast")
        for bank_id, sub in feat.groupby("bank_id"):
            series = sub.set_index("period_ts")[metric]
            for _, row in sub.iterrows():
                value = row[metric]
                # DATA_GAP: legal-critical rule but missing value for this bank-period.
                if is_legal_critical and operator != "missing" and _as_float(value) is None:
                    findings.append(_data_gap_row(rule, bank_id, row["bank_name"],
                                                  row["period"], row["period_ts"],
                                                  note="Thiếu giá trị để kiểm tra rule pháp lý bắt buộc"))
                    continue
                if trend_op:
                    fires = _trend_fires(operator, series, row["period_ts"], threshold)
                else:
                    fires = _evaluate(operator, value, threshold)
                if fires:
                    findings.append({
                        "bank_id": bank_id, "bank_name": row["bank_name"],
                        "period": row["period"], "period_ts": row["period_ts"],
                        "rule_id": rule["rule_id"], "rule_name": rule.get("rule_name"),
                        "metric": metric, "metric_value": _as_float(value),
                        "operator": operator, "threshold": _fmt_threshold(threshold),
                        "severity": severity, "status": status,
                        "risk_domain": rule.get("risk_domain"),
                        "legal_source": rule.get("legal_source"),
                        "article_reference": rule.get("article_reference"),
                        "finding_type": "VIOLATION",
                        "description": rule.get("description"),
                        "audit_recommendation": rule.get("audit_recommendation"),
                    })
    cols = ["bank_id", "bank_name", "period", "period_ts", "rule_id", "rule_name",
            "metric", "metric_value", "operator", "threshold", "severity", "status",
            "risk_domain", "legal_source", "article_reference", "finding_type",
            "description", "audit_recommendation"]
    df = pd.DataFrame(findings, columns=cols)
    LOG.info("Rule engine: %d findings (%d VIOLATION, %d DATA_GAP)",
             len(df), (df["finding_type"] == "VIOLATION").sum() if not df.empty else 0,
             (df["finding_type"] == "DATA_GAP").sum() if not df.empty else 0)
    return df


def _special_control_rows(feat: pd.DataFrame, excluded: dict) -> list[dict]:
    """Một finding/bank-period cho đơn vị không được so ngưỡng (KSĐB).

    Không sinh theo từng rule để tránh nhân bản; mục đích chỉ là để KTV không hiểu
    nhầm "không có cờ vi phạm" = "tuân thủ tốt".
    """
    if not excluded:
        return []
    sub = feat[feat["bank_id"].isin(excluded)]
    rows = []
    for _, row in sub.iterrows():
        reason = excluded[row["bank_id"]]
        rows.append({
            "bank_id": row["bank_id"], "bank_name": row["bank_name"],
            "period": row["period"], "period_ts": row["period_ts"],
            "rule_id": "SPECIAL_CONTROL_NO_THRESHOLD",
            "rule_name": "Không áp ngưỡng giám sát (kiểm soát đặc biệt/can thiệp sớm)",
            "metric": None, "metric_value": None,
            "operator": None, "threshold": None,
            "severity": "INFO", "status": "ACTIVE",
            "risk_domain": "governance",
            "legal_source": "QĐ 682/QĐ-TTGSNH4 ngày 30/10/2024",
            "article_reference": "Phụ lục 3, mục 3.2 — trường hợp không sử dụng ngưỡng",
            "finding_type": "SPECIAL_CONTROL",
            "description": f"Không so ngưỡng giám sát QĐ 682/618: {reason}",
            "audit_recommendation": "Đánh giá theo quy định pháp luật về kiểm soát đặc biệt/can thiệp sớm — KHÔNG kết luận tuân thủ dựa trên việc không có cờ vi phạm.",
        })
    return rows


def _evaluate_tiered_rule(rule: dict, feat: pd.DataFrame, inst_types: dict,
                          excluded: dict) -> list[dict]:
    """Áp ngưỡng 3 bậc theo loại hình TCTD (QĐ 682 / QĐ 618)."""
    _check_tier_order(rule)
    metric = rule.get("metric")
    direction = rule.get("direction")
    by_type = rule.get("tiers_by_type") or {}
    status = rule.get("status", "ACTIVE")
    is_legal_critical = rule.get("severity") == "CRITICAL"
    rows: list[dict] = []

    if metric not in feat.columns:
        if is_legal_critical:
            rows.append(_data_gap_row(rule, None, None, None, None,
                                      note="Chỉ tiêu không có trong dữ liệu"))
        return rows

    for _, row in feat.iterrows():
        bank_id = row["bank_id"]
        if bank_id in excluded:
            continue                      # KSĐB: đã có finding SPECIAL_CONTROL riêng
        tiers = by_type.get(inst_types.get(bank_id))
        if not tiers:
            continue                      # QĐ không quy định ngưỡng cho loại hình này
        value = row[metric]
        if _as_float(value) is None:
            if is_legal_critical:
                rows.append(_data_gap_row(
                    rule, bank_id, row["bank_name"], row["period"], row["period_ts"],
                    note="Thiếu giá trị để kiểm tra ngưỡng giám sát bắt buộc"))
            continue
        tier = _tier_for(value, tiers, direction)
        if tier is None:
            continue
        finding_type, severity = TIER_MEANING[tier]
        rows.append({
            "bank_id": bank_id, "bank_name": row["bank_name"],
            "period": row["period"], "period_ts": row["period_ts"],
            "rule_id": rule["rule_id"], "rule_name": rule.get("rule_name"),
            "metric": metric, "metric_value": _as_float(value),
            "operator": "<" if direction == "lower_riskier" else ">",
            "threshold": _fmt_threshold(_as_float(tiers.get(tier))),
            "severity": severity, "status": status,
            "risk_domain": rule.get("risk_domain"),
            "legal_source": rule.get("legal_source"),
            "article_reference": rule.get("article_reference"),
            "finding_type": finding_type,
            "description": (
                f"{rule.get('rule_name')}: giá trị {_as_float(value):.2f}% so với "
                f"Ngưỡng {tier[-1]} = {_as_float(tiers.get(tier))}% "
                f"(loại hình: {inst_types.get(bank_id)}). {TIER_ACTION[tier]}"),
            "audit_recommendation": rule.get("audit_recommendation"),
        })
    return rows


def _fmt_threshold(threshold) -> str:
    if threshold is None:
        return ""
    if isinstance(threshold, (list, tuple)):
        return f"[{threshold[0]}, {threshold[1]}]"
    return str(threshold)


def _data_gap_row(rule, bank_id, bank_name, period, period_ts, note):
    return {
        "bank_id": bank_id, "bank_name": bank_name, "period": period, "period_ts": period_ts,
        "rule_id": rule["rule_id"], "rule_name": rule.get("rule_name"),
        "metric": rule.get("metric"), "metric_value": None,
        "operator": rule.get("operator"), "threshold": _fmt_threshold(rule.get("threshold")),
        "severity": "DATA_GAP", "status": rule.get("status", "ACTIVE"),
        "risk_domain": rule.get("risk_domain"), "legal_source": rule.get("legal_source"),
        "article_reference": rule.get("article_reference"), "finding_type": "DATA_GAP",
        "description": f"{note}: {rule.get('rule_name')}",
        "audit_recommendation": "Yêu cầu bổ sung dữ liệu để kiểm tra rule pháp lý bắt buộc.",
    }


def summarize_by_bank_period(findings: pd.DataFrame) -> pd.DataFrame:
    """Aggregate findings to one row per bank-period with severity counts and the
    worst severity (used by risk scoring for the rule floor)."""
    if findings is None or findings.empty:
        return pd.DataFrame(columns=["bank_id", "period", "worst_severity",
                                     "n_critical", "n_high", "n_medium", "n_low",
                                     "n_data_gap", "n_findings"])
    rows = []
    for (bid, period), sub in findings.groupby(["bank_id", "period"]):
        counts = sub["severity"].value_counts().to_dict()
        sev_present = [s for s in SEVERITY_ORDER if counts.get(s, 0) > 0]
        worst = sev_present[-1] if sev_present else (
            "DATA_GAP" if counts.get("DATA_GAP", 0) else "INFO")
        rows.append({
            "bank_id": bid, "period": period,
            "period_ts": sub["period_ts"].iloc[0],
            "bank_name": sub["bank_name"].iloc[0],
            "worst_severity": worst,
            "n_critical": int(counts.get("CRITICAL", 0)),
            "n_high": int(counts.get("HIGH", 0)),
            "n_medium": int(counts.get("MEDIUM", 0)),
            "n_low": int(counts.get("LOW", 0)),
            "n_data_gap": int(counts.get("DATA_GAP", 0)),
            "n_findings": int(len(sub)),
        })
    return pd.DataFrame(rows)
