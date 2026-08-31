"""Early Warning System (EWS) — cảnh báo sớm rủi ro an toàn hoạt động ngân hàng.

Unlike the rule engine (current breaches) and risk_scoring (instantaneous state),
the EWS is built from *leading* indicators so it flags deterioration BEFORE it
becomes a CRITICAL legal breach:

  * proximity-to-limit  — how deep a metric sits in the soft-warning buffer band,
  * trend / momentum    — oriented slope over a lookback window,
  * acceleration        — change of slope (deterioration speeding up),
  * volatility spike     — recent dispersion vs baseline,
  * breach streak        — consecutive periods inside/over the soft band,
  * anomaly persistence  — share of recent periods flagged anomalous,
  * projected breach     — extrapolated number of periods until the metric hits the
                           regulatory limit (an explicit "early" horizon).

Outputs a per bank-period EWS table (score 0..100 + level NORMAL/WATCH/WARNING/ALARM
+ signal breakdown + drivers + projected breach), a system-level EWS timeline, and an
"emerging risk" watchlist (banks escalating fastest). Recommended frequency: monthly.

All thresholds/weights come from config/ews_config.yaml — nothing is hard-coded.
EWS is decision support, not a prediction of certain failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .utils import DATA_ROOT, LOG, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]
LEVEL_RANK = {"NORMAL": 0, "WATCH": 1, "WARNING": 2, "ALARM": 3}
RANK_LEVEL = {v: k for k, v in LEVEL_RANK.items()}


@dataclass
class EWSResult:
    frequency: str
    table: pd.DataFrame = field(default_factory=pd.DataFrame)        # per bank-period
    latest: pd.DataFrame = field(default_factory=pd.DataFrame)       # latest period per bank
    system: pd.DataFrame = field(default_factory=pd.DataFrame)       # per-period system EWS
    emerging: pd.DataFrame = field(default_factory=pd.DataFrame)     # escalating watchlist
    metrics_used: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Per-metric leading signals (computed on one bank's sorted series)
# --------------------------------------------------------------------------- #
def _slope(values: np.ndarray) -> float:
    """Least-squares slope per period over the (already trimmed) window."""
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    try:
        return float(np.polyfit(x, values, 1)[0])
    except (np.linalg.LinAlgError, ValueError):
        return 0.0


def _proximity(value: float, limit: float, buffer: float, direction: str) -> float:
    """0..1 how close `value` is to the limit within the soft band (>=1 if breached)."""
    if direction == "higher_safer":
        # safe when value >= limit + buffer; danger grows as value falls toward limit.
        return float(np.clip((limit + buffer - value) / buffer, 0.0, 1.0))
    # lower_safer: safe when value <= limit - buffer; danger grows as value rises.
    return float(np.clip((value - (limit - buffer)) / buffer, 0.0, 1.0))


def _adverse_rate(slope: float, direction: str) -> float:
    """Per-period adverse movement (positive = worsening)."""
    return -slope if direction == "higher_safer" else slope


def _metric_signals(series: pd.Series, mcfg: dict, lookback: int,
                    min_points: int, horizon: int) -> dict | None:
    """Compute leading signals for one metric on one bank (latest point = last row)."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    # Drop implausible values (unit glitches / zero-as-missing) so they don't drive
    # false alarms; they remain visible via validation.py as OUT_OF_RANGE.
    plaus = mcfg.get("plausible")
    if plaus:
        lo, hi = float(plaus[0]), float(plaus[1])
        s = s[(s >= lo) & (s <= hi)]
    if s.empty:
        return {"data_gap": True, "metric": mcfg["name"],
                "label": mcfg.get("label", mcfg["name"]), "domain": mcfg.get("domain")}
    value = float(s.iloc[-1])
    window = s.iloc[-lookback:]
    direction = mcfg["direction"]
    limit, buffer = float(mcfg["limit"]), float(mcfg["buffer"])

    prox = _proximity(value, limit, buffer, direction)

    # Trend: total adverse move over the window scaled by buffer/dispersion.
    trend = accel = vol = 0.0
    streak = 0
    proj_periods = None
    if len(window) >= min_points:
        vals = window.to_numpy(dtype=float)
        slope = _slope(vals)
        adverse = _adverse_rate(slope, direction)
        scale = max(buffer, float(np.nanstd(vals)) or buffer, 1e-9)
        trend = float(np.clip(adverse * len(vals) / scale, 0.0, 1.0))

        # Acceleration: slope of recent half vs earlier half.
        if len(vals) >= 4:
            half = len(vals) // 2
            a0 = _adverse_rate(_slope(vals[:half + 1]), direction)
            a1 = _adverse_rate(_slope(vals[half:]), direction)
            accel = float(np.clip((a1 - a0) * len(vals) / scale, 0.0, 1.0))

        # Volatility spike: recent std vs longer baseline std.
        base = pd.to_numeric(s, errors="coerce").dropna()
        if len(base) >= 4:
            recent_std = float(np.nanstd(vals))
            base_std = float(np.nanstd(base.to_numpy(dtype=float))) or 1e-9
            vol = float(np.clip((recent_std / base_std - 1.0), 0.0, 1.0))

        # Projected periods until breach (heading adverse and not yet over limit).
        breached_now = (value < limit) if direction == "higher_safer" else (value > limit)
        if not breached_now and adverse > 1e-9:
            dist = (value - limit) if direction == "higher_safer" else (limit - value)
            if dist > 0:
                proj_periods = float(min(horizon + 1, dist / adverse))

    # Breach streak: consecutive most-recent periods inside/over the soft band.
    band_start = (limit + buffer) if direction == "higher_safer" else (limit - buffer)
    for v in reversed(s.to_numpy(dtype=float)[-lookback:]):
        inside = (v <= band_start) if direction == "higher_safer" else (v >= band_start)
        if inside:
            streak += 1
        else:
            break
    streak_norm = float(min(1.0, streak / max(1, lookback)))

    breached = (value < limit) if direction == "higher_safer" else (value > limit)
    return {
        "metric": mcfg["name"], "label": mcfg.get("label", mcfg["name"]),
        "domain": mcfg.get("domain"), "weight": float(mcfg.get("weight", 1.0)),
        "value": value, "limit": limit, "direction": direction,
        "proximity": prox, "trend": trend, "acceleration": accel,
        "volatility": vol, "breach_streak": streak_norm,
        "in_buffer": prox > 0, "breached": bool(breached),
        "proj_periods": proj_periods,
    }


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
def compute_ews(features: pd.DataFrame, frequency: str = "monthly",
                anomaly_table: pd.DataFrame | None = None,
                cfg: dict | None = None) -> EWSResult:
    """Compute the EWS table for every bank-period in `features`."""
    if features is None or features.empty:
        return EWSResult(frequency=frequency)
    cfg = cfg or load_config("ews_config")
    lookback = cfg.get("lookback", 6)
    horizon = cfg.get("projection_horizon", 12)
    min_points = cfg.get("min_points", 3)
    sig_w = cfg.get("signal_weights", {})
    esc = cfg.get("escalation", {})
    metrics_cfg = [m for m in cfg.get("metrics", []) if m["name"] in features.columns]
    metrics_used = [m["name"] for m in metrics_cfg]
    if not metrics_cfg:
        LOG.warning("EWS: none of the configured metrics present for %s", frequency)
        return EWSResult(frequency=frequency, config=cfg)

    # Per-bank anomaly history (period_ts -> anomaly_label) for persistence signal.
    anom_map: dict = {}
    if anomaly_table is not None and not anomaly_table.empty and "anomaly_label" in anomaly_table.columns:
        for bid, sub in anomaly_table.groupby("bank_id"):
            anom_map[bid] = sub.set_index("period")["anomaly_label"].to_dict()

    feat = features.sort_values(["bank_id", "period_ts"])
    rows = []
    for bid, sub in feat.groupby("bank_id"):
        sub = sub.reset_index(drop=True)
        bname = sub["bank_name"].iloc[0] if "bank_name" in sub.columns else bid
        periods = sub["period"].tolist()
        for i in range(len(sub)):
            hist = sub.iloc[: i + 1]               # data available up to this period
            sigs, n_gap = [], 0
            for mcfg in metrics_cfg:
                ms = _metric_signals(hist[mcfg["name"]], mcfg, lookback, min_points, horizon)
                if ms is None or ms.get("data_gap"):
                    n_gap += int(ms is not None)
                    continue
                sigs.append(ms)
            if not sigs:
                continue

            # Anomaly persistence over the recent lookback window for this bank.
            anom_persist = 0.0
            amap = anom_map.get(bid, {})
            if amap:
                recent = periods[max(0, i - lookback + 1): i + 1]
                flags = [amap.get(p, 0) for p in recent]
                anom_persist = float(np.mean(flags)) if flags else 0.0

            row = _aggregate_signals(bid, bname, sub.loc[i, "period"],
                                     sub.loc[i, "period_ts"], sigs, sig_w,
                                     anom_persist, esc, horizon)
            row["n_data_gap"] = n_gap
            rows.append(row)

    if not rows:
        return EWSResult(frequency=frequency, config=cfg, metrics_used=metrics_used)
    table = pd.DataFrame(rows).sort_values(["bank_id", "period_ts"]).reset_index(drop=True)

    # Escalation vs the bank's previous period (delta + direction).
    table["prev_score"] = table.groupby("bank_id")["ews_score"].shift(1)
    table["score_delta"] = (table["ews_score"] - table["prev_score"]).round(1)
    table["prev_level_rank"] = table.groupby("bank_id")["level_rank"].shift(1)
    table["escalating"] = (table["level_rank"] > table["prev_level_rank"].fillna(table["level_rank"]))

    latest = (table.sort_values("period_ts").groupby("bank_id", as_index=False).tail(1)
              .sort_values("ews_score", ascending=False).reset_index(drop=True))
    system = _system_ews(table, cfg)
    emerging = _emerging(latest, cfg)

    LOG.info("EWS[%s]: %d bank-periods | ALARM=%d WARNING=%d (latest)",
             frequency, len(table),
             int((latest["ews_level"] == "ALARM").sum()),
             int((latest["ews_level"] == "WARNING").sum()))
    return EWSResult(frequency=frequency, table=table, latest=latest, system=system,
                     emerging=emerging, metrics_used=metrics_used, config=cfg)


def _aggregate_signals(bid, bname, period, period_ts, sigs, sig_w, anom_persist,
                       esc, horizon) -> dict:
    """Combine per-metric signals (weighted) into one bank-period EWS row."""
    wsum = sum(s["weight"] for s in sigs) or 1.0

    def wavg(key):
        return sum(s[key] * s["weight"] for s in sigs) / wsum

    # Proximity uses weighted max-ish blend (a single near-limit metric matters).
    prox_mean = wavg("proximity")
    prox_max = max(s["proximity"] for s in sigs)
    proximity = 0.6 * prox_max + 0.4 * prox_mean

    signals = {
        "proximity": proximity,
        "trend": wavg("trend"),
        "acceleration": wavg("acceleration"),
        "volatility": wavg("volatility"),
        "breach_streak": wavg("breach_streak"),
        "anomaly_persistence": anom_persist,
    }
    score = 100.0 * sum(sig_w.get(k, 0.0) * v for k, v in signals.items())
    score = float(np.clip(score, 0, 100))

    # Projected breach: nearest metric heading toward its limit.
    proj = [(s["proj_periods"], s["label"]) for s in sigs if s["proj_periods"] is not None]
    proj_periods, proj_metric = (min(proj, key=lambda x: x[0]) if proj else (None, None))

    any_in_buffer = any(s["in_buffer"] for s in sigs)
    any_breached = any(s["breached"] for s in sigs)
    adverse_trend = signals["trend"] >= 0.3

    level, rank = _level_from_score(score, esc, any_in_buffer, any_breached,
                                    adverse_trend, proj_periods)

    # Drivers: top contributing (metric, dominant signal) for explanation.
    drivers = sorted(sigs, key=lambda s: max(s["proximity"], s["trend"], s["breach_streak"]),
                     reverse=True)[:3]
    driver_txt = "; ".join(
        f"{d['label']}={d['value']:.2f} (prox {d['proximity']:.2f}, trend {d['trend']:.2f})"
        for d in drivers)
    domains = sorted({s["domain"] for s in sigs
                      if (s["proximity"] > 0.3 or s["trend"] > 0.3) and s["domain"]})

    return {
        "bank_id": bid, "bank_name": bname, "period": period, "period_ts": period_ts,
        "ews_score": round(score, 1), "ews_level": level, "level_rank": rank,
        "ews_label": _label_for(level),
        "sig_proximity": round(signals["proximity"] * 100, 1),
        "sig_trend": round(signals["trend"] * 100, 1),
        "sig_acceleration": round(signals["acceleration"] * 100, 1),
        "sig_volatility": round(signals["volatility"] * 100, 1),
        "sig_breach_streak": round(signals["breach_streak"] * 100, 1),
        "sig_anomaly_persistence": round(signals["anomaly_persistence"] * 100, 1),
        "projected_breach_metric": proj_metric,
        "projected_periods_to_breach": (round(proj_periods, 1)
                                        if proj_periods is not None and proj_periods <= horizon
                                        else None),
        "risk_domains": ", ".join(domains),
        "drivers": driver_txt,
        "n_in_buffer": sum(1 for s in sigs if s["in_buffer"]),
        "n_breached": sum(1 for s in sigs if s["breached"]),
    }


_LABELS = {"NORMAL": "Bình thường", "WATCH": "Theo dõi",
           "WARNING": "Cảnh báo", "ALARM": "Báo động"}


def _label_for(level: str) -> str:
    return _LABELS.get(level, level)


def _level_from_score(score, esc, any_in_buffer, any_breached, adverse_trend,
                      proj_periods) -> tuple[str, int]:
    if score <= 25:
        level = "NORMAL"
    elif score <= 50:
        level = "WATCH"
    elif score <= 75:
        level = "WARNING"
    else:
        level = "ALARM"
    rank = LEVEL_RANK[level]

    # Escalation floors from hard leading signals.
    if any_in_buffer:
        rank = max(rank, LEVEL_RANK.get(esc.get("near_limit_min_level", "WATCH"), 1))
    if any_breached:
        rank = max(rank, LEVEL_RANK.get(esc.get("breached_min_level", "WARNING"), 2))
        if adverse_trend:
            rank = max(rank, LEVEL_RANK.get(esc.get("breached_worsening_min_level", "ALARM"), 3))
    if proj_periods is not None and proj_periods <= esc.get("projected_breach_periods", 3):
        rank = max(rank, LEVEL_RANK.get("WARNING", 2))
    return RANK_LEVEL[rank], rank


def _system_ews(table: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    sysc = cfg.get("system", {})
    rows = []
    for (period, ts), sub in table.groupby(["period", "period_ts"]):
        n = len(sub)
        warn_plus = int((sub["level_rank"] >= 2).sum())
        share = warn_plus / n if n else 0.0
        sys_level = "NORMAL"
        if share >= sysc.get("warn_share_alarm", 0.30):
            sys_level = "ALARM"
        elif share >= sysc.get("warn_share_warning", 0.20):
            sys_level = "WARNING"
        elif sub["ews_score"].mean() >= 40:
            sys_level = "WATCH"
        rows.append({
            "period": period, "period_ts": ts,
            "mean_ews": round(float(sub["ews_score"].mean()), 1),
            "n_banks": n, "n_alarm": int((sub["ews_level"] == "ALARM").sum()),
            "n_warning": int((sub["ews_level"] == "WARNING").sum()),
            "n_warning_plus": warn_plus,
            "share_warning_plus": round(share * 100, 1),
            "system_level": sys_level, "system_label": _label_for(sys_level),
        })
    res = pd.DataFrame(rows).sort_values("period_ts").reset_index(drop=True)
    if not res.empty:
        res["mean_ews_mom"] = res["mean_ews"].diff().round(1)
    return res


def _emerging(latest: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Banks whose EWS is rising fastest or that escalated a level — 'rủi ro mới nổi'."""
    if latest.empty:
        return latest
    jump = cfg.get("emerging", {}).get("score_jump", 12)
    mask = (latest["score_delta"].fillna(0) >= jump) | (latest["escalating"].fillna(False))
    cols = ["bank_id", "bank_name", "period", "ews_score", "ews_level", "ews_label",
            "score_delta", "escalating", "projected_periods_to_breach",
            "projected_breach_metric", "risk_domains", "drivers"]
    out = latest[mask][[c for c in cols if c in latest.columns]]
    return out.sort_values("score_delta", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    from .feature_engineering import build_features
    from .anomaly_detection import run_isolation_forest
    res = load_all(DATA_ROOT, use_cache=True)
    feats = build_features(res.wide["monthly"], "monthly")
    an = run_isolation_forest(feats, feats.attrs["base_metrics"])
    ews = compute_ews(feats, "monthly", an.table)
    print("Metrics used:", ews.metrics_used)
    print("\nLatest EWS (top 12):")
    print(ews.latest[["bank_id", "period", "ews_score", "ews_level",
                      "projected_periods_to_breach", "projected_breach_metric",
                      "drivers"]].head(12).to_string(index=False))
    print("\nSystem EWS (tail):")
    print(ews.system[["period", "mean_ews", "share_warning_plus", "system_level"]]
          .tail(6).to_string(index=False))
    print("\nEmerging watchlist:", len(ews.emerging))
    print(ews.emerging[["bank_id", "period", "ews_score", "ews_level", "score_delta"]]
          .head(10).to_string(index=False))
