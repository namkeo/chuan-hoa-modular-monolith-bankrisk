"""Stress testing — sức chịu đựng vốn & thanh khoản trước kịch bản khủng hoảng.

For the latest snapshot of each bank, apply each configured scenario's shocks and
measure resilience on two axes:

  CAPITAL — a credit shock (NPL ratio rises by ``npl_shock_pp``) generates incremental
    bad debt; the loss (× LGD) erodes own funds, while ``rwa_shock`` inflates RWA.
        stressed_CAR = (own_funds − credit_loss) / (RWA × (1 + rwa_shock))
    Reported: baseline/stressed CAR, capital shortfall to the 8% floor, pass/fail, and
    a *reverse stress* "breaking point": how many extra NPL pp push CAR to 8%.

  LIQUIDITY — a funding shock (deposit run-off + wholesale run-off + HQLA haircut).
    With HQLA available: LCR = haircut HQLA / stressed net outflow.
    Without HQLA (this dataset): stressed-LDR / funding gap after the deposit run-off.

Missing base amounts are derived where possible (e.g. RWA = own_funds / CAR,
npl_amount = loans × npl_ratio); otherwise the cell is flagged DATA_GAP. Recommended
frequency: monthly (carries CAR / RWA / own funds and deposits / loans).

This is hypothetical scenario analysis to support audit — NOT a forecast. Assumptions
(LGD, run-off rates, RWA shock) must be reviewed by the auditor for the context.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .utils import DATA_ROOT, LOG, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]


@dataclass
class StressResult:
    frequency: str
    results: pd.DataFrame = field(default_factory=pd.DataFrame)        # bank × scenario
    system: pd.DataFrame = field(default_factory=pd.DataFrame)         # per scenario
    breaking_points: pd.DataFrame = field(default_factory=pd.DataFrame)  # reverse stress
    scenarios: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    snapshot_period: str | None = None


# --------------------------------------------------------------------------- #
# Base-quantity derivation (robust to missing amount columns)
# --------------------------------------------------------------------------- #
def _num(row: pd.Series, col: str):
    if col not in row.index:
        return None
    v = row.get(col)
    try:
        f = float(v)
        return f if f == f else None  # filter NaN
    except (TypeError, ValueError):
        return None


def _derive_inputs(row: pd.Series) -> dict:
    """Extract / derive the quantities a stress test needs from one bank-period row."""
    gaps = []
    loans = _num(row, "customer_loans")
    if loans is None:
        loans = _num(row, "total_loans")
    deposits = _num(row, "deposits") or _num(row, "total_deposits")
    npl_ratio = _num(row, "npl_ratio")
    npl_amount = _num(row, "npl_amount")
    if npl_amount is None and loans is not None and npl_ratio is not None:
        npl_amount = loans * npl_ratio / 100.0     # derive from ratio

    car = _num(row, "car_solo")
    if car is None:
        car = _num(row, "car_consolidated")
    # Reject implausible CAR (unit glitches / zero-as-missing) before deriving RWA.
    if car is not None and not (1.0 <= car <= 50.0):
        car = None
    own_funds = _num(row, "own_capital_solo") or _num(row, "tier1_capital") or _num(row, "equity")
    if own_funds is not None and own_funds <= 0:
        own_funds = None
    rwa = _num(row, "rwa") or _num(row, "rwa_credit")
    if rwa is not None and rwa <= 0:
        rwa = None
    # Cross-derive the capital triangle (CAR = own_funds / RWA).
    if rwa is None and own_funds is not None and car not in (None, 0):
        rwa = own_funds / (car / 100.0)
    if car is None and own_funds is not None and rwa not in (None, 0):
        car = own_funds / rwa * 100.0
    if own_funds is None and rwa is not None and car is not None:
        own_funds = car / 100.0 * rwa
    # Final capital sanity: need a plausible CAR and positive own funds / RWA.
    if car is None or not (1.0 <= car <= 50.0) or not own_funds or not rwa:
        car = own_funds = rwa = None

    hqla = _num(row, "hqla")
    wholesale = _num(row, "interbank_funding")
    if wholesale is None:
        st_fund = _num(row, "short_term_funding")
        wholesale = max(0.0, st_fund - (deposits or 0.0)) if st_fund is not None else None

    # Liquidity sanity: positive deposits/loans and a plausible baseline LDR.
    # Null deposits (not loans — loans still feeds the capital side) to flag the gap.
    base_ldr = (loans / deposits * 100.0) if (loans and deposits and deposits > 0) else None
    if not loans or not deposits or base_ldr is None or not (1.0 <= base_ldr <= 400.0):
        deposits = None
    if own_funds is None or rwa is None or car is None:
        gaps.append("capital")     # cannot run capital stress
    if deposits is None or loans is None:
        gaps.append("liquidity")
    return {
        "loans": loans, "deposits": deposits, "npl_ratio": npl_ratio,
        "npl_amount": npl_amount, "car": car, "own_funds": own_funds, "rwa": rwa,
        "hqla": hqla, "wholesale": wholesale, "ldr": _num(row, "ldr"),
        "total_assets": _num(row, "total_assets") or loans, "data_gaps": gaps,
    }


# --------------------------------------------------------------------------- #
# Scenario application
# --------------------------------------------------------------------------- #
def _apply_capital(inp: dict, sc: dict, min_car: float, default_lgd: float) -> dict:
    if "capital" in inp["data_gaps"] or inp["loans"] is None or inp["npl_ratio"] is None:
        return {"capital_status": "DATA_GAP"}
    own = inp["own_funds"]
    rwa = inp["rwa"]
    loans = inp["loans"]
    lgd = float(sc.get("lgd", default_lgd))
    npl_shock_pp = float(sc.get("npl_shock_pp", 0.0))
    rwa_shock = float(sc.get("rwa_shock", 0.0))

    incremental_bad = loans * npl_shock_pp / 100.0
    credit_loss = incremental_bad * lgd
    own_stressed = own - credit_loss
    rwa_stressed = rwa * (1.0 + rwa_shock)
    car0 = own / rwa * 100.0 if rwa else None
    car1 = own_stressed / rwa_stressed * 100.0 if rwa_stressed else None
    shortfall = max(0.0, min_car / 100.0 * rwa_stressed - own_stressed)
    return {
        "capital_status": "OK",
        "baseline_car": round(car0, 2) if car0 is not None else None,
        "stressed_car": round(car1, 2) if car1 is not None else None,
        "car_delta": round(car1 - car0, 2) if (car0 is not None and car1 is not None) else None,
        "credit_loss": round(credit_loss, 1),
        "capital_shortfall": round(shortfall, 1),
        "passes_capital": bool(car1 is not None and car1 >= min_car),
    }


def _apply_liquidity(inp: dict, sc: dict, cfg_liq: dict) -> dict:
    if "liquidity" in inp["data_gaps"]:
        return {"liquidity_status": "DATA_GAP"}
    deposits = inp["deposits"]
    loans = inp["loans"]
    wholesale = inp["wholesale"] or 0.0
    dep_runoff = float(sc.get("deposit_runoff", 0.0))
    who_runoff = float(sc.get("wholesale_runoff", 0.0))
    haircut = float(sc.get("hqla_haircut", 0.0))

    outflow = deposits * dep_runoff + wholesale * who_runoff
    hqla = inp["hqla"]
    if cfg_liq.get("use_hqla_if_available", True) and hqla is not None and outflow > 0:
        available = hqla * (1.0 - haircut)
        lcr = available / outflow * 100.0
        gap = max(0.0, outflow - available)
        return {
            "liquidity_status": "OK", "liq_method": "LCR",
            "stressed_lcr": round(lcr, 1),
            "liquidity_gap": round(gap, 1),
            "deposit_outflow": round(outflow, 1),
            "passes_liquidity": bool(lcr >= cfg_liq.get("lcr_min", 100.0)),
        }
    # Fallback: stressed LDR / funding gap (no HQLA in the data).
    stressed_dep = deposits * (1.0 - dep_runoff)
    stressed_ldr = loans / stressed_dep * 100.0 if stressed_dep > 0 else float("inf")
    funding_gap = max(0.0, loans - stressed_dep)
    limit = cfg_liq.get("stressed_ldr_limit", 100.0)
    return {
        "liquidity_status": "OK", "liq_method": "STRESSED_LDR",
        "baseline_ldr": round(loans / deposits * 100.0, 1) if deposits else None,
        "stressed_ldr": round(stressed_ldr, 1) if np.isfinite(stressed_ldr) else None,
        "liquidity_gap": round(funding_gap, 1),
        "deposit_outflow": round(deposits * dep_runoff, 1),
        "passes_liquidity": bool(np.isfinite(stressed_ldr) and stressed_ldr <= limit),
    }


def _breaking_point_npl(inp: dict, min_car: float, default_lgd: float) -> dict:
    """Reverse stress: extra NPL pp (pure credit, no RWA shock) to push CAR to min."""
    if "capital" in inp["data_gaps"] or inp["loans"] in (None, 0):
        return {"breaking_npl_pp": None, "already_below": None}
    own, rwa, loans = inp["own_funds"], inp["rwa"], inp["loans"]
    lgd = default_lgd
    capital_buffer = own - min_car / 100.0 * rwa     # own funds above the 8% floor
    if capital_buffer <= 0:
        return {"breaking_npl_pp": 0.0, "already_below": True}
    pp = capital_buffer / (loans * lgd) * 100.0
    return {"breaking_npl_pp": round(pp, 2), "already_below": False}


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def run_stress_test(features: pd.DataFrame, frequency: str = "monthly",
                    cfg: dict | None = None, all_periods: bool = True) -> StressResult:
    """Run all scenarios on each bank's balance sheet.

    With ``all_periods=True`` (default) the test is computed for every bank-period so
    the dashboard's time selector can show stress results "as of" any chosen period;
    the ``system`` summary and ``snapshot_period`` still refer to the latest period.
    """
    if features is None or features.empty:
        return StressResult(frequency=frequency)
    cfg = cfg or load_config("stress_scenarios")
    scenarios = cfg.get("scenarios", [])
    min_car = cfg.get("capital", {}).get("min_car", 8.0)
    cfg_liq = cfg.get("liquidity", {})
    default_lgd = cfg.get("assumptions", {}).get("lgd", 0.55)

    feat_sorted = features.sort_values(["bank_id", "period_ts"])
    latest = feat_sorted.groupby("bank_id", as_index=False).tail(1).reset_index(drop=True)
    snapshot_period = latest["period"].mode().iloc[0] if not latest.empty else None
    targets = feat_sorted.reset_index(drop=True) if all_periods else latest

    rows, breaking = [], []
    for _, srow in targets.iterrows():
        inp = _derive_inputs(srow)
        bp = _breaking_point_npl(inp, min_car, default_lgd)
        breaking.append({
            "bank_id": srow["bank_id"], "bank_name": srow.get("bank_name", srow["bank_id"]),
            "period": srow["period"],
            "baseline_car": round(inp["car"], 2) if inp["car"] is not None else None,
            "breaking_npl_pp": bp["breaking_npl_pp"],
            "already_below_min": bp["already_below"],
        })
        for sc in scenarios:
            cap = _apply_capital(inp, sc, min_car, default_lgd)
            liq = _apply_liquidity(inp, sc, cfg_liq)
            rows.append({
                "bank_id": srow["bank_id"],
                "bank_name": srow.get("bank_name", srow["bank_id"]),
                "period": srow["period"],
                "scenario_id": sc["id"], "scenario_name": sc.get("name", sc["id"]),
                "total_assets": inp["total_assets"],
                **cap, **liq,
                "data_gaps": ",".join(inp["data_gaps"]) if inp["data_gaps"] else "",
            })
    results = pd.DataFrame(rows)
    breaking_df = pd.DataFrame(breaking)        # all periods; consumers filter by period
    # System summary refers to the latest snapshot period.
    latest_results = (results[results["period"] == snapshot_period]
                      if not results.empty else results)
    system = _system_summary(latest_results, scenarios)
    LOG.info("Stress test[%s]: %d banks × %d scenarios × %d periods (snapshot %s)",
             frequency, targets["bank_id"].nunique(), len(scenarios),
             targets["period"].nunique() if all_periods else 1, snapshot_period)
    return StressResult(frequency=frequency, results=results, system=system,
                        breaking_points=breaking_df, scenarios=scenarios, config=cfg,
                        snapshot_period=snapshot_period)


def _system_summary(results: pd.DataFrame, scenarios: list[dict]) -> pd.DataFrame:
    if results is None or results.empty:
        return pd.DataFrame()
    rows = []
    for sc in scenarios:
        sub = results[results["scenario_id"] == sc["id"]]
        cap = sub[sub.get("capital_status") == "OK"] if "capital_status" in sub else sub.iloc[0:0]
        liq = sub[sub.get("liquidity_status") == "OK"] if "liquidity_status" in sub else sub.iloc[0:0]
        fail_cap = cap[cap["passes_capital"] == False] if not cap.empty else cap  # noqa: E712
        fail_liq = liq[liq["passes_liquidity"] == False] if not liq.empty else liq  # noqa: E712
        assets_total = cap["total_assets"].sum() if not cap.empty else 0.0
        assets_fail = fail_cap["total_assets"].sum() if not fail_cap.empty else 0.0
        rows.append({
            "scenario_id": sc["id"], "scenario_name": sc.get("name", sc["id"]),
            "description": sc.get("description", ""),
            "n_assessed_capital": int(len(cap)),
            "n_fail_capital": int(len(fail_cap)),
            "total_capital_shortfall": round(float(fail_cap["capital_shortfall"].sum()), 1) if not fail_cap.empty else 0.0,
            "min_stressed_car": round(float(cap["stressed_car"].min()), 2) if not cap.empty else None,
            "avg_stressed_car": round(float(cap["stressed_car"].mean()), 2) if not cap.empty else None,
            "assets_share_failing": round(assets_fail / assets_total * 100, 1) if assets_total else 0.0,
            "n_assessed_liquidity": int(len(liq)),
            "n_fail_liquidity": int(len(fail_liq)),
            "total_liquidity_gap": round(float(fail_liq["liquidity_gap"].sum()), 1) if not fail_liq.empty else 0.0,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    from .feature_engineering import build_features
    res = load_all(DATA_ROOT, use_cache=True)
    feats = build_features(res.wide["monthly"], "monthly")
    st = run_stress_test(feats, "monthly")
    print("Snapshot:", st.snapshot_period)
    print("\nSystem summary:")
    print(st.system[["scenario_name", "n_fail_capital", "total_capital_shortfall",
                     "min_stressed_car", "n_fail_liquidity", "total_liquidity_gap"]].to_string(index=False))
    print("\nSevere scenario — worst banks by stressed CAR:")
    sev = st.results[st.results["scenario_id"] == "severe"]
    print(sev[sev["capital_status"] == "OK"].sort_values("stressed_car")[
        ["bank_id", "baseline_car", "stressed_car", "capital_shortfall", "passes_capital"]]
        .head(10).to_string(index=False))
    print("\nReverse stress — smallest NPL shock to breach 8% CAR:")
    print(st.breaking_points[st.breaking_points["breaking_npl_pp"].notna()][
        ["bank_id", "baseline_car", "breaking_npl_pp", "already_below_min"]].head(10).to_string(index=False))
