"""Cross-frequency feature integration ("combined" view).

The SBV performance indicator set is reported at different natural frequencies:
capital / liquidity ratios (CAR, LDR, ST-funding) come monthly, asset-quality and
balance-sheet amounts (NPL amount, provisions, equity, total assets, LLR coverage)
come quarterly, and profitability (ROA, ROE, NIM, CIR, profit) comes yearly.

Running each frequency in isolation therefore starves every model of half the
picture. This module builds a single **combined** wide table on the finest grain
(monthly) and enriches every bank-month with the most recent available value from the
coarser frequencies via a point-in-time **as-of backward join** (no look-ahead):
a 2025-08 row receives the 2025Q2 NPL/provisions and the 2024 ROA/NIM, each carried
forward only within a staleness tolerance.

The result feeds the existing feature engineering, rule engine, Isolation Forest,
K-means, risk scoring, EWS and stress test unchanged — they simply see a much richer
feature set. A ``source_map`` records which frequency each metric came from so the UI
can show provenance.
"""
from __future__ import annotations

import pandas as pd

from .utils import DATA_ROOT, LOG

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]
FINE_TO_COARSE = ["monthly", "quarterly", "yearly"]

# Default staleness tolerance (days) a coarser value may be carried forward.
DEFAULT_TOLERANCE_DAYS = {"quarterly": 130, "yearly": 430}


def _metric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ID_COLS
            and pd.api.types.is_numeric_dtype(df[c])]


def build_combined_wide(wide: dict[str, pd.DataFrame],
                        cfg: dict | None = None) -> pd.DataFrame | None:
    """Build a monthly-grain wide table enriched with as-of quarterly + yearly metrics.

    Returns None when there is no monthly base (or nothing to combine). The returned
    frame carries ``.attrs['source_map']`` (metric -> provenance) and
    ``.attrs['base_frequency']`` / ``.attrs['enriched_from']``.
    """
    cfg = cfg or {}
    mf_cfg = cfg.get("multi_frequency", {})
    tol_days = {**DEFAULT_TOLERANCE_DAYS, **mf_cfg.get("tolerance_days", {})}

    # Base = finest sub-annual frequency available (prefer monthly).
    base_freq = next((f for f in ("monthly", "daily", "quarterly") if f in wide
                      and not wide[f].empty), None)
    if base_freq is None:
        return None
    coarser = [f for f in ("quarterly", "yearly")
               if f in wide and not wide[f].empty and f != base_freq]
    if not coarser:
        return None  # nothing to combine

    base = wide[base_freq].copy()
    base["period_ts"] = pd.to_datetime(base["period_ts"])
    base = base.sort_values("period_ts").reset_index(drop=True)

    # Provenance: every base metric starts owned by the base frequency.
    source_map: dict[str, dict] = {
        m: {"sources": [base_freq], "primary": base_freq} for m in _metric_cols(base)
    }
    enriched_from = []

    for freq in coarser:
        src = wide[freq][["bank_id", "period_ts"] + _metric_cols(wide[freq])].copy()
        src["period_ts"] = pd.to_datetime(src["period_ts"])
        src = src.sort_values("period_ts").reset_index(drop=True)
        metrics = _metric_cols(wide[freq])
        if not metrics:
            continue
        # Rename source metrics to a temp namespace to avoid collisions on merge.
        ren = {m: f"__{freq}__{m}" for m in metrics}
        src = src.rename(columns=ren)
        tol = pd.Timedelta(days=tol_days.get(freq, 365))
        merged = pd.merge_asof(
            base, src, on="period_ts", by="bank_id",
            direction="backward", tolerance=tol)

        added = filled = 0
        for m in metrics:
            tmp = f"__{freq}__{m}"
            if tmp not in merged.columns:
                continue
            if m in base.columns:
                # Coalesce: keep base value, fill gaps from the coarser as-of value.
                before = base[m].notna().sum()
                base[m] = base[m].fillna(merged[tmp])
                gained = base[m].notna().sum() - before
                if gained > 0:
                    filled += 1
                    sm = source_map.setdefault(m, {"sources": [base_freq], "primary": base_freq})
                    if freq not in sm["sources"]:
                        sm["sources"].append(freq)
            else:
                # New metric only available at a coarser frequency.
                base[m] = merged[tmp]
                added += 1
                source_map[m] = {"sources": [freq], "primary": freq}
        enriched_from.append({"frequency": freq, "metrics_added": added,
                              "metrics_filled": filled})
        LOG.info("Combined: enriched from %s (+%d new metrics, filled %d sparse)",
                 freq, added, filled)

    base.attrs["source_map"] = source_map
    base.attrs["base_frequency"] = base_freq
    base.attrs["enriched_from"] = enriched_from
    base.attrs["combined"] = True
    LOG.info("Combined wide: %d bank-periods × %d metrics (base=%s, enriched from %s)",
             len(base), len(_metric_cols(base)), base_freq,
             ", ".join(c["frequency"] for c in enriched_from))
    return base


def source_map_table(combined: pd.DataFrame) -> pd.DataFrame:
    """Flatten the source map into a tidy table for display."""
    sm = combined.attrs.get("source_map", {}) if combined is not None else {}
    rows = [{"metric": m, "primary_frequency": v["primary"],
             "sources": ", ".join(v["sources"]),
             "is_cross_frequency": len(v["sources"]) > 1}
            for m, v in sorted(sm.items())]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    from .utils import load_config
    res = load_all(DATA_ROOT, use_cache=True)
    combined = build_combined_wide(res.wide, load_config("model_config"))
    if combined is None:
        print("No combinable frequencies.")
    else:
        print(f"Combined: {combined.shape} | base={combined.attrs['base_frequency']}")
        print("Enriched from:", combined.attrs["enriched_from"])
        smt = source_map_table(combined)
        print(f"\nMetrics by source ({len(smt)} total):")
        print(smt["primary_frequency"].value_counts().to_string())
        print("\nCross-frequency-filled metrics:")
        print(smt[smt["is_cross_frequency"]][["metric", "sources"]].head(20).to_string(index=False))
