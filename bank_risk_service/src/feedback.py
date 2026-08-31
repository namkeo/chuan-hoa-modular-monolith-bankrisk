"""Auditor feedback capture and iterative-improvement loop.

Auditors label findings (anomalies / rule alerts) so the system can learn which
signals are useful. Feedback is appended to ``data/feedback/feedback.csv``.

On a subsequent run the loop:
  * computes false-positive rates per metric / model,
  * proposes *soft* threshold / contamination / k adjustments (returned as
    suggestions, never auto-applied),
  * NEVER edits mandatory legal rules without explicit user confirmation.

Feedback labels: confirmed_anomaly, false_positive, needs_more_data,
accepted_risk, escalated_to_audit.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from .utils import FEEDBACK_DIR, LOG

FEEDBACK_CSV = FEEDBACK_DIR / "feedback.csv"

FEEDBACK_LABELS = ["confirmed_anomaly", "false_positive", "needs_more_data",
                   "accepted_risk", "escalated_to_audit"]

FEEDBACK_COLUMNS = ["feedback_ts", "bank_id", "period", "source",
                    "item_id", "label", "metric", "note", "auditor"]


def record_feedback(*, bank_id: str, period: str | None, source: str,
                    label: str, item_id: str = "", metric: str = "",
                    note: str = "", auditor: str = "") -> pd.DataFrame:
    """Append one feedback row. ``source`` in {anomaly, rule, risk_score, cluster}."""
    if label not in FEEDBACK_LABELS:
        LOG.warning("Unknown feedback label '%s' (allowed: %s)", label, FEEDBACK_LABELS)
    row = {
        "feedback_ts": datetime.now().isoformat(timespec="seconds"),
        "bank_id": bank_id, "period": period, "source": source,
        "item_id": item_id, "label": label, "metric": metric,
        "note": note, "auditor": auditor,
    }
    df = pd.DataFrame([row], columns=FEEDBACK_COLUMNS)
    if FEEDBACK_CSV.exists():
        try:
            prev = pd.read_csv(FEEDBACK_CSV)
            df = pd.concat([prev, df], ignore_index=True)
        except Exception:  # noqa: BLE001
            pass
    df.to_csv(FEEDBACK_CSV, index=False, encoding="utf-8-sig")
    LOG.info("Recorded feedback (%s/%s) -> %s", source, label, FEEDBACK_CSV.name)
    return df


def load_feedback() -> pd.DataFrame:
    if FEEDBACK_CSV.exists():
        try:
            return pd.read_csv(FEEDBACK_CSV)
        except Exception:  # noqa: BLE001
            return pd.DataFrame(columns=FEEDBACK_COLUMNS)
    return pd.DataFrame(columns=FEEDBACK_COLUMNS)


def false_positive_stats(feedback: pd.DataFrame | None = None) -> dict:
    """Overall and per-source/per-metric false-positive rates."""
    fb = feedback if feedback is not None else load_feedback()
    if fb is None or fb.empty:
        return {"overall_fp_rate": None, "by_source": {}, "by_metric": {}, "n_feedback": 0}
    labeled = fb[fb["label"].isin(["confirmed_anomaly", "false_positive"])]
    if labeled.empty:
        return {"overall_fp_rate": None, "by_source": {}, "by_metric": {}, "n_feedback": len(fb)}

    def fp_rate(sub):
        n = len(sub)
        return round((sub["label"] == "false_positive").sum() / n, 4) if n else None

    return {
        "overall_fp_rate": fp_rate(labeled),
        "by_source": {s: fp_rate(g) for s, g in labeled.groupby("source")},
        "by_metric": {m: fp_rate(g) for m, g in labeled.groupby("metric") if m},
        "n_feedback": len(fb),
    }


def suggest_adjustments(feedback: pd.DataFrame | None = None,
                        cfg: dict | None = None) -> list[dict]:
    """Propose soft tuning suggestions from feedback. Returns a list of dicts:
    {target, current, suggested, reason}. These are advisory only.

    Legal mandatory rules (CRITICAL/ACTIVE) are explicitly excluded — the function
    will only suggest reviewing them, never changing the threshold.
    """
    from .utils import load_config
    cfg = cfg or load_config("model_config")
    stats = false_positive_stats(feedback)
    suggestions: list[dict] = []
    overall = stats["overall_fp_rate"]
    if overall is None:
        return suggestions

    contamination = cfg.get("isolation_forest", {}).get("contamination", 0.08)
    if overall >= 0.4:
        suggestions.append({
            "target": "isolation_forest.contamination",
            "current": contamination,
            "suggested": round(max(0.02, contamination * 0.75), 3),
            "reason": f"Tỷ lệ false-positive cao ({overall*100:.0f}%) — giảm contamination để bớt cảnh báo nhiễu.",
        })
    elif overall <= 0.1 and stats["n_feedback"] >= 20:
        suggestions.append({
            "target": "isolation_forest.contamination",
            "current": contamination,
            "suggested": round(min(0.15, contamination * 1.25), 3),
            "reason": f"False-positive thấp ({overall*100:.0f}%) — có thể tăng độ nhạy (contamination).",
        })

    # Per-metric soft rule severity downgrade suggestions (early-warning rules only).
    rules_cfg = load_config("regulatory_rules")
    legal_locked = {r["rule_id"] for r in rules_cfg.get("rules", [])
                    if r.get("severity") == "CRITICAL" and r.get("status", "ACTIVE") == "ACTIVE"}
    for metric, rate in stats["by_metric"].items():
        if rate is not None and rate >= 0.5:
            related = [r["rule_id"] for r in rules_cfg.get("rules", [])
                       if r.get("metric") == metric and r["rule_id"] not in legal_locked]
            if related:
                suggestions.append({
                    "target": f"rule_severity:{','.join(related)}",
                    "current": "as configured",
                    "suggested": "review / soften (non-legal)",
                    "reason": f"Chỉ tiêu '{metric}' có FP {rate*100:.0f}% — cân nhắc hạ severity cảnh báo (không áp dụng cho rule pháp lý bắt buộc).",
                })

    if legal_locked:
        suggestions.append({
            "target": "legal_rules",
            "current": sorted(legal_locked),
            "suggested": "KHÔNG tự động sửa",
            "reason": "Rule pháp lý bắt buộc chỉ được thay đổi sau khi KTV xác nhận với văn bản gốc.",
        })
    return suggestions


def _main(argv: list[str]) -> int:
    """CLI used by the web backend: read one JSON feedback object from --json or stdin.

    Example: python -m src.feedback --json '{"bank_id":"ACB","period":"2025Q4",
             "source":"anomaly","label":"false_positive","note":"..."}'
    """
    import json
    import sys
    payload = None
    if "--json" in argv:
        payload = argv[argv.index("--json") + 1]
    else:
        data = sys.stdin.read().strip()
        payload = data or "{}"
    try:
        obj = json.loads(payload)
        record_feedback(
            bank_id=obj.get("bank_id", ""), period=obj.get("period"),
            source=obj.get("source", "manual"), label=obj.get("label", "needs_more_data"),
            item_id=obj.get("item_id", ""), metric=obj.get("metric", ""),
            note=obj.get("note", ""), auditor=obj.get("auditor", "web"))
        print(json.dumps({"ok": True}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
