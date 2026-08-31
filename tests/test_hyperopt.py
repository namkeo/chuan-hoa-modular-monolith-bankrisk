"""Tests for hyperparameter tuning and the tuned-config merge."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.hyperopt import (apply_tuned, current_tuned, reset_tuned,
                          tune_isolation_forest, tune_kmeans, TUNED_PATH)
from src.utils import effective_model_config, load_config


def _panel(n_banks=12, n_periods=8):
    rng = np.random.default_rng(0)
    rows = []
    periods = pd.period_range("2024-01", periods=n_periods, freq="M")
    for b in range(n_banks):
        base = rng.normal(0, 1, 5)
        for per in periods:
            vals = base + rng.normal(0, 0.2, 5)
            rows.append({
                "bank_id": f"B{b}", "bank_name": f"B{b}", "period": str(per),
                "period_ts": per.to_timestamp(how="end").normalize(),
                "npl_ratio": 2 + vals[0], "ldr": 75 + vals[1] * 5,
                "car_solo": 11 + vals[2], "roa": 1 + vals[3] * 0.3,
                "group2_ratio": 2 + vals[4],
            })
    df = pd.DataFrame(rows)
    df.attrs["base_metrics"] = ["npl_ratio", "ldr", "car_solo", "roa", "group2_ratio"]
    return df


def test_tune_isolation_forest_returns_leaderboard():
    feats = _panel()
    tr = tune_isolation_forest(feats, feats.attrs["base_metrics"],
                               space={"contamination": [0.05, 0.10],
                                      "n_estimators": [100], "max_samples": ["auto"]})
    assert not tr.leaderboard.empty
    assert {"contamination", "n_estimators", "max_samples", "criterion_score"}.issubset(
        tr.leaderboard.columns)
    assert "contamination" in tr.best
    assert tr.criterion in ("stability", "separation", "feedback")


def test_tune_kmeans_picks_valid_k():
    feats = _panel()
    tr = tune_kmeans(feats, feats.attrs["base_metrics"], space={"k_min": 2, "k_max": 5})
    assert not tr.leaderboard.empty
    assert tr.best.get("manual_k", 0) >= 2
    assert tr.leaderboard["silhouette"].notna().all()


def test_apply_and_effective_config_merge():
    try:
        apply_tuned(isolation_forest={"contamination": 0.123, "n_estimators": 222,
                                      "max_samples": 0.66})
        cur = current_tuned()
        assert cur["applied"] is True
        eff = effective_model_config()
        assert eff["isolation_forest"]["contamination"] == 0.123
        assert eff["isolation_forest"]["n_estimators"] == 222
        assert eff.get("_tuned_applied") is True
        # Reset disables the override.
        reset_tuned()
        eff2 = effective_model_config()
        base = load_config("model_config")
        assert eff2["isolation_forest"]["contamination"] == base["isolation_forest"]["contamination"]
    finally:
        # Clean up the tuned file so it doesn't affect other runs.
        if TUNED_PATH.exists():
            TUNED_PATH.unlink()
