"""K-means risk segmentation of banks (optionally per period) with automatic k
selection and cluster risk profiling, plus a 2-D projection (PCA, UMAP if available)
for visualization only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.metrics import (calinski_harabasz_score, davies_bouldin_score,
                             silhouette_score)
from sklearn.preprocessing import StandardScaler

from .utils import LOG, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]

# Metrics used to label a cluster's risk character (oriented: + = worse).
PROFILE_METRICS = {
    "npl_ratio": +1, "group2_ratio": +1, "ldr": +1, "st_funding_for_mlt_loans": +1,
    "credit_growth_yoy": +1, "cir": +1,
    "car_solo": -1, "car_consolidated": -1, "roa": -1, "roe": -1,
    "liquidity_reserve_ratio": -1, "llr_coverage": -1,
}


@dataclass
class ClusterResult:
    table: pd.DataFrame                 # ID cols + cluster_id, cluster_risk_label
    k: int = 0
    metrics: dict = field(default_factory=dict)   # k -> {silhouette, db, ch}
    profiles: pd.DataFrame = field(default_factory=pd.DataFrame)
    projection: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_names: list[str] = field(default_factory=list)


def _prep_matrix(features: pd.DataFrame, base_metrics, min_ratio):
    if base_metrics:
        cols = [m for m in base_metrics if m in features.columns]
    else:
        cols = [c for c in features.columns if c not in ID_COLS
                and pd.api.types.is_numeric_dtype(features[c])]
    cols = [c for c in cols if features[c].notna().mean() >= min_ratio]
    X = SimpleImputer(strategy="median").fit_transform(features[cols])
    X = StandardScaler().fit_transform(X)
    return X, cols


def select_k(X: np.ndarray, k_min: int, k_max: int, method: str, seed: int):
    """Evaluate k across the range; return (best_k, metrics_by_k)."""
    metrics = {}
    k_max = min(k_max, len(X) - 1)
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=seed)
        labels = km.fit_predict(X)
        if len(set(labels)) < 2:
            continue
        metrics[k] = {
            "silhouette": float(silhouette_score(X, labels)),
            "davies_bouldin": float(davies_bouldin_score(X, labels)),
            "calinski_harabasz": float(calinski_harabasz_score(X, labels)),
        }
    if not metrics:
        return k_min, metrics
    if method == "davies_bouldin":
        best = min(metrics, key=lambda k: metrics[k]["davies_bouldin"])
    elif method == "calinski_harabasz":
        best = max(metrics, key=lambda k: metrics[k]["calinski_harabasz"])
    else:  # silhouette default
        best = max(metrics, key=lambda k: metrics[k]["silhouette"])
    return best, metrics


def _risk_label(profile_row: pd.Series, all_profiles: pd.DataFrame) -> str:
    """Heuristic descriptive label from a cluster's mean profile vs other clusters."""
    tags = []
    def hi(metric):  # is this cluster high on metric relative to others?
        if metric not in all_profiles.columns:
            return False
        return profile_row.get(metric) >= all_profiles[metric].quantile(0.66)
    def lo(metric):
        if metric not in all_profiles.columns:
            return False
        return profile_row.get(metric) <= all_profiles[metric].quantile(0.34)

    if hi("npl_ratio") or hi("group2_ratio"):
        tags.append("tín dụng xấu")
    if hi("credit_growth_yoy"):
        tags.append("tăng trưởng nóng")
    if hi("ldr") or hi("st_funding_for_mlt_loans") or lo("liquidity_reserve_ratio"):
        tags.append("thanh khoản yếu")
    if lo("roa") or lo("roe"):
        tags.append("lợi nhuận suy giảm")
    if lo("car_solo") or lo("car_consolidated"):
        tags.append("vốn mỏng")
    if not tags:
        tags.append("an toàn")
    return ", ".join(tags)


def _composite_risk_score(profiles: pd.DataFrame) -> pd.Series:
    """0..1 risk score per cluster from oriented, normalized profile metrics."""
    score = pd.Series(0.0, index=profiles.index)
    n = 0
    for m, sign in PROFILE_METRICS.items():
        if m not in profiles.columns:
            continue
        col = profiles[m]
        rng = col.max() - col.min()
        if rng == 0 or np.isnan(rng):
            continue
        norm = (col - col.min()) / rng
        score += sign * norm if sign > 0 else (1 - norm)
        n += 1
    return score / n if n else score


def run_kmeans(features: pd.DataFrame, base_metrics: list[str] | None = None,
               cfg: dict | None = None, k: int | None = None) -> ClusterResult:
    """Cluster the latest snapshot per bank (or all bank-periods if no period_ts)."""
    if features is None or features.empty:
        return ClusterResult(table=pd.DataFrame())
    cfg = cfg or load_config("model_config")
    kp = cfg.get("kmeans", {})
    pre = cfg.get("preprocessing", {})
    seed = cfg.get("random_state", 42)

    X, cols = _prep_matrix(features, base_metrics, pre.get("min_non_null_ratio", 0.3))
    if X.shape[1] < 2 or len(X) < 4:
        LOG.warning("Not enough data for K-means (%s)", X.shape)
        out = features[ID_COLS].copy()
        out["cluster_id"] = 0
        out["cluster_risk_label"] = "n/a"
        return ClusterResult(table=out, feature_names=cols)

    if k is None:
        if kp.get("k_selection") == "manual":
            k = kp.get("manual_k", 4)
            _, metrics = select_k(X, kp.get("k_min", 2), kp.get("k_max", 10),
                                  "silhouette", seed)
        else:
            k, metrics = select_k(X, kp.get("k_min", 2), kp.get("k_max", 10),
                                  kp.get("k_selection", "silhouette"), seed)
    else:
        _, metrics = select_k(X, kp.get("k_min", 2), kp.get("k_max", 10), "silhouette", seed)
    k = max(2, min(k, len(X) - 1))

    km = KMeans(n_clusters=k, n_init=kp.get("n_init", 10),
                max_iter=kp.get("max_iter", 300), random_state=seed)
    labels = km.fit_predict(X)

    out = features[ID_COLS].copy()
    out["cluster_id"] = labels

    # Cluster mean profiles (original units), risk score + descriptive label.
    prof_df = features[cols].copy()
    prof_df["cluster_id"] = labels
    profiles = prof_df.groupby("cluster_id").mean(numeric_only=True)
    profiles["n_banks"] = pd.Series(labels).value_counts().sort_index().values
    risk_score = _composite_risk_score(profiles)
    profiles["cluster_risk_score"] = (risk_score * 100).round(1)
    labels_map = {cid: _risk_label(profiles.loc[cid], profiles) for cid in profiles.index}
    # Rank clusters by risk for an ordinal risk tag.
    order = risk_score.sort_values().index.tolist()
    rank_tag = {cid: i for i, cid in enumerate(order)}
    tag_names = {0: "an toàn nhất"}
    out["cluster_risk_label"] = out["cluster_id"].map(labels_map)
    out["cluster_risk_score"] = out["cluster_id"].map(profiles["cluster_risk_score"])
    profiles["cluster_risk_label"] = profiles.index.map(labels_map)

    # 2-D projection (PCA) for visualization.
    projection = pd.DataFrame()
    try:
        coords = PCA(n_components=2, random_state=seed).fit_transform(X)
        projection = out[ID_COLS + ["cluster_id"]].copy()
        projection["x"] = coords[:, 0]
        projection["y"] = coords[:, 1]
    except Exception as exc:  # noqa: BLE001
        LOG.warning("PCA projection failed: %s", exc)

    LOG.info("K-means: k=%d, silhouette=%.3f", k,
             metrics.get(k, {}).get("silhouette", float("nan")))
    return ClusterResult(table=out, k=k, metrics=metrics, profiles=profiles.reset_index(),
                         projection=projection, feature_names=cols)


def latest_snapshot(features: pd.DataFrame) -> pd.DataFrame:
    """Most recent period per bank — the natural unit for cross-sectional clustering."""
    if features is None or features.empty:
        return features
    return (features.sort_values("period_ts")
            .groupby("bank_id", as_index=False).tail(1)
            .reset_index(drop=True))
