"""Anomaly detection with Isolation Forest over the bank-period feature matrix.

Includes preprocessing (winsorization, median imputation, scaling), system-wide and
per-frequency training, anomaly score/rank, and per-row explanation via feature
deviation (signed z-score of the most extreme contributing features).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, StandardScaler

from .utils import LOG, MODELS_DIR, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]


@dataclass
class AnomalyResult:
    table: pd.DataFrame          # ID cols + anomaly_score, anomaly_label, anomaly_rank, top_features
    feature_names: list[str]
    model_path: str | None = None


def _select_feature_matrix(features: pd.DataFrame, base_metrics: list[str] | None,
                           min_ratio: float) -> tuple[pd.DataFrame, list[str]]:
    """Choose numeric, sufficiently-populated columns for the model."""
    if base_metrics:
        cols = [m for m in base_metrics if m in features.columns]
    else:
        cols = [c for c in features.columns if c not in ID_COLS
                and pd.api.types.is_numeric_dtype(features[c])]
    cols = [c for c in cols if features[c].notna().mean() >= min_ratio]
    return features[cols].copy(), cols


def _winsorize(df: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        ql, qh = out[c].quantile(lo), out[c].quantile(hi)
        out[c] = out[c].clip(ql, qh)
    return out


def run_isolation_forest(features: pd.DataFrame, base_metrics: list[str] | None = None,
                         cfg: dict | None = None, save_as: str | None = None) -> AnomalyResult:
    """Fit Isolation Forest and score every bank-period.

    anomaly_score is normalized to 0..100 (higher = more anomalous).
    """
    if features is None or features.empty:
        return AnomalyResult(table=pd.DataFrame(), feature_names=[])
    cfg = cfg or load_config("model_config")
    pre = cfg.get("preprocessing", {})
    ifp = cfg.get("isolation_forest", {})
    seed = cfg.get("random_state", 42)

    X_raw, cols = _select_feature_matrix(features, base_metrics,
                                         pre.get("min_non_null_ratio", 0.3))
    if X_raw.shape[1] < 2 or len(X_raw) < 5:
        LOG.warning("Not enough data for Isolation Forest (%s)", X_raw.shape)
        base = features[ID_COLS].copy()
        base["anomaly_score"] = np.nan
        base["anomaly_label"] = 0
        base["anomaly_rank"] = np.nan
        base["top_features"] = ""
        return AnomalyResult(table=base, feature_names=cols)

    lo, hi = pre.get("winsorize_quantiles", [0.01, 0.99])
    X_w = _winsorize(X_raw, lo, hi)
    imputer = SimpleImputer(strategy=pre.get("impute_strategy", "median"))
    X_imp = imputer.fit_transform(X_w)
    scaler = RobustScaler() if pre.get("scaler") == "robust" else StandardScaler()
    X_scaled = scaler.fit_transform(X_imp)

    model = IsolationForest(
        n_estimators=ifp.get("n_estimators", 300),
        contamination=ifp.get("contamination", 0.08),
        max_samples=ifp.get("max_samples", "auto"),
        bootstrap=ifp.get("bootstrap", False),
        random_state=seed, n_jobs=-1,
    )
    model.fit(X_scaled)
    raw_scores = -model.score_samples(X_scaled)   # higher = more anomalous
    labels = (model.predict(X_scaled) == -1).astype(int)

    smin, smax = raw_scores.min(), raw_scores.max()
    norm = 100 * (raw_scores - smin) / (smax - smin) if smax > smin else np.zeros_like(raw_scores)

    # Explanation: signed z of each scaled feature; pick top |z| per row.
    top_k = ifp.get("top_features", 6)
    z = pd.DataFrame(X_scaled, columns=cols, index=features.index)
    explanations = []
    for idx in z.index:
        row = z.loc[idx]
        top = row.reindex(row.abs().sort_values(ascending=False).index)[:top_k]
        explanations.append("; ".join(f"{c}({v:+.1f})" for c, v in top.items()))

    out = features[ID_COLS].copy()
    out["anomaly_score"] = np.round(norm, 2)
    out["anomaly_label"] = labels
    out["anomaly_rank"] = pd.Series(norm, index=out.index).rank(ascending=False).astype(int)
    out["top_features"] = explanations

    model_path = None
    if save_as:
        model_path = str(MODELS_DIR / f"isoforest_{save_as}.joblib")
        joblib.dump({"model": model, "scaler": scaler, "imputer": imputer, "cols": cols}, model_path)
        meta = {"frequency": save_as, "n_features": len(cols), "features": cols,
                "params": ifp, "n_rows": int(len(out)),
                "anomaly_rate": float(labels.mean()), "seed": seed}
        Path(MODELS_DIR / f"isoforest_{save_as}_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        LOG.info("Saved Isolation Forest model -> %s", model_path)

    LOG.info("Isolation Forest: %d rows, %d features, anomaly rate %.1f%%",
             len(out), len(cols), labels.mean() * 100)
    return AnomalyResult(table=out, feature_names=cols, model_path=model_path)


def run_peer_group_isolation(features: pd.DataFrame, group_col: str = "cluster_id",
                             base_metrics: list[str] | None = None,
                             cfg: dict | None = None) -> pd.DataFrame:
    """Optional: train one Isolation Forest per peer group for within-peer anomalies."""
    if group_col not in features.columns:
        LOG.info("Peer-group column '%s' absent — skipping peer-group anomalies", group_col)
        return pd.DataFrame()
    parts = []
    for gid, sub in features.groupby(group_col):
        if len(sub) < 8:
            continue
        res = run_isolation_forest(sub, base_metrics, cfg)
        t = res.table.copy()
        t["peer_group"] = gid
        t = t.rename(columns={"anomaly_score": "peer_anomaly_score",
                              "anomaly_label": "peer_anomaly_label"})
        parts.append(t[ID_COLS + ["peer_group", "peer_anomaly_score", "peer_anomaly_label"]])
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
