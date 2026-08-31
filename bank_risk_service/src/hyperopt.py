"""Hyperparameter fine-tuning for the unsupervised ML models.

Grid-searches Isolation Forest and K-means configurations and ranks them by a
criterion, then lets the auditor *apply* the best config (persisted to
config/tuned_params.yaml, picked up by ``effective_model_config``).

Because the task is unsupervised, "best" needs an explicit criterion:

  Isolation Forest
    - ``feedback``  : if auditor feedback exists (confirmed_anomaly / false_positive),
                      maximise agreement (F1) of the model's flags with those labels.
    - ``stability`` : agreement of anomaly labels across several random seeds
                      (a stable detector is preferable when no labels exist).
    - ``separation``: normalised gap between flagged vs non-flagged score means.

  K-means
    - silhouette / davies_bouldin / calinski_harabasz over a range of k.

Nothing is auto-applied: tuning returns a leaderboard + recommendation; applying is
an explicit, reversible action.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import (calinski_harabasz_score, davies_bouldin_score,
                             silhouette_score)
from sklearn.preprocessing import RobustScaler, StandardScaler

from .utils import CONFIG_DIR, DATA_ROOT, LOG, load_config

ID_COLS = ["bank_id", "bank_name", "period", "period_ts"]
TUNED_PATH = CONFIG_DIR / "tuned_params.yaml"


@dataclass
class TuneResult:
    model: str
    criterion: str
    leaderboard: pd.DataFrame = field(default_factory=pd.DataFrame)
    best: dict = field(default_factory=dict)
    current: dict = field(default_factory=dict)
    n_samples: int = 0
    note: str = ""


# --------------------------------------------------------------------------- #
# Shared preprocessing (mirrors anomaly_detection / clustering)
# --------------------------------------------------------------------------- #
def _matrix(features: pd.DataFrame, base_metrics, cfg) -> tuple[np.ndarray, list[str]]:
    pre = cfg.get("preprocessing", {})
    min_ratio = pre.get("min_non_null_ratio", 0.3)
    if base_metrics:
        cols = [m for m in base_metrics if m in features.columns]
    else:
        cols = [c for c in features.columns if c not in ID_COLS
                and pd.api.types.is_numeric_dtype(features[c])]
    cols = [c for c in cols if features[c].notna().mean() >= min_ratio]
    if not cols:
        return np.empty((0, 0)), []
    X = features[cols].copy()
    lo, hi = pre.get("winsorize_quantiles", [0.01, 0.99])
    for c in X.columns:
        X[c] = X[c].clip(X[c].quantile(lo), X[c].quantile(hi))
    X = SimpleImputer(strategy=pre.get("impute_strategy", "median")).fit_transform(X)
    scaler = RobustScaler() if pre.get("scaler") == "robust" else StandardScaler()
    return scaler.fit_transform(X), cols


# --------------------------------------------------------------------------- #
# Isolation Forest tuning
# --------------------------------------------------------------------------- #
def _feedback_labels(features: pd.DataFrame) -> dict[tuple, int]:
    """Map (bank_id, period) -> 1 (confirmed anomaly) / 0 (false positive)."""
    from .feedback import load_feedback
    fb = load_feedback()
    if fb is None or fb.empty:
        return {}
    fb = fb[fb["source"] == "anomaly"] if "source" in fb.columns else fb
    out = {}
    for _, r in fb.iterrows():
        if r.get("label") == "confirmed_anomaly":
            out[(r.get("bank_id"), str(r.get("period")))] = 1
        elif r.get("label") == "false_positive":
            out[(r.get("bank_id"), str(r.get("period")))] = 0
    return out


def tune_isolation_forest(features: pd.DataFrame, base_metrics=None,
                          space: dict | None = None, criterion: str = "auto",
                          cfg: dict | None = None) -> TuneResult:
    cfg = cfg or load_config("model_config")
    seed = cfg.get("random_state", 42)
    X, cols = _matrix(features, base_metrics, cfg)
    if X.shape[0] < 8 or X.shape[1] < 2:
        return TuneResult("isolation_forest", criterion, note="Không đủ dữ liệu để tinh chỉnh.")

    space = space or {}
    contaminations = space.get("contamination", [0.03, 0.05, 0.08, 0.10, 0.15])
    n_estimators = space.get("n_estimators", [100, 200, 400])
    max_samples = space.get("max_samples", ["auto", 0.75])

    labels = _feedback_labels(features)
    if criterion == "auto":
        criterion = "feedback" if len(labels) >= 5 else "stability"

    idx = features.reset_index(drop=True)[["bank_id", "period"]]
    rows = []
    for cont, n_est, ms in product(contaminations, n_estimators, max_samples):
        scores_seeds, labels_seeds = [], []
        for s in (seed, seed + 1, seed + 2):
            model = IsolationForest(n_estimators=n_est, contamination=cont,
                                    max_samples=ms, random_state=s, n_jobs=-1)
            model.fit(X)
            raw = -model.score_samples(X)
            flag = (model.predict(X) == -1).astype(int)
            scores_seeds.append(raw)
            labels_seeds.append(flag)
        flag0 = labels_seeds[0]
        anomaly_rate = float(np.mean(flag0))

        stability = _label_agreement(labels_seeds)
        separation = _score_separation(scores_seeds[0], flag0)
        fb_f1, fb_n = _feedback_f1(idx, flag0, labels)

        crit_value = {"feedback": fb_f1 if fb_f1 is not None else np.nan,
                      "stability": stability,
                      "separation": separation}.get(criterion, stability)
        rows.append({
            "contamination": cont, "n_estimators": n_est,
            "max_samples": ms, "anomaly_rate_pct": round(anomaly_rate * 100, 2),
            "stability": round(stability, 4), "separation": round(separation, 4),
            "feedback_f1": round(fb_f1, 4) if fb_f1 is not None else None,
            "feedback_n": fb_n,
            "criterion_score": round(float(crit_value), 4) if crit_value == crit_value else None,
        })
    lb = pd.DataFrame(rows)
    valid = lb.dropna(subset=["criterion_score"])
    if valid.empty:
        valid = lb.assign(criterion_score=lb["stability"])
    best_row = valid.sort_values("criterion_score", ascending=False).iloc[0]
    best = {"contamination": float(best_row["contamination"]),
            "n_estimators": int(best_row["n_estimators"]),
            "max_samples": (best_row["max_samples"]
                            if best_row["max_samples"] == "auto" else float(best_row["max_samples"]))}
    current = {k: cfg.get("isolation_forest", {}).get(k)
               for k in ("contamination", "n_estimators", "max_samples")}
    note = {"feedback": f"Tối ưu theo phản hồi KTV ({len(labels)} nhãn).",
            "stability": "Không có nhãn phản hồi — tối ưu theo độ ổn định giữa các seed.",
            "separation": "Tối ưu theo độ tách điểm bất thường."}.get(criterion, "")
    return TuneResult("isolation_forest", criterion,
                      leaderboard=lb.sort_values("criterion_score", ascending=False).reset_index(drop=True),
                      best=best, current=current, n_samples=int(X.shape[0]), note=note)


def _label_agreement(label_sets: list[np.ndarray]) -> float:
    """Mean pairwise agreement of binary labels across seeds (1 = identical)."""
    if len(label_sets) < 2:
        return 1.0
    agrees = []
    for i in range(len(label_sets)):
        for j in range(i + 1, len(label_sets)):
            agrees.append(float(np.mean(label_sets[i] == label_sets[j])))
    return float(np.mean(agrees)) if agrees else 1.0


def _score_separation(scores: np.ndarray, flags: np.ndarray) -> float:
    """Normalised gap between mean anomaly score of flagged vs non-flagged."""
    if flags.sum() == 0 or flags.sum() == len(flags):
        return 0.0
    sd = scores.std() or 1e-9
    return float((scores[flags == 1].mean() - scores[flags == 0].mean()) / sd)


def _feedback_f1(idx: pd.DataFrame, flags: np.ndarray, labels: dict):
    """F1 of model flags vs auditor labels on the labelled subset."""
    if not labels:
        return None, 0
    tp = fp = fn = n = 0
    for i, (_, r) in enumerate(idx.iterrows()):
        key = (r["bank_id"], str(r["period"]))
        if key in labels:
            n += 1
            pred, truth = int(flags[i]), labels[key]
            if pred == 1 and truth == 1:
                tp += 1
            elif pred == 1 and truth == 0:
                fp += 1
            elif pred == 0 and truth == 1:
                fn += 1
    if n == 0 or (tp == 0 and fp == 0 and fn == 0):
        return None, n
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return f1, n


# --------------------------------------------------------------------------- #
# K-means tuning
# --------------------------------------------------------------------------- #
def tune_kmeans(features: pd.DataFrame, base_metrics=None, space: dict | None = None,
                criterion: str = "silhouette", cfg: dict | None = None) -> TuneResult:
    from .clustering import latest_snapshot
    cfg = cfg or load_config("model_config")
    seed = cfg.get("random_state", 42)
    snap = latest_snapshot(features)
    X, cols = _matrix(snap, base_metrics, cfg)
    if X.shape[0] < 4 or X.shape[1] < 2:
        return TuneResult("kmeans", criterion, note="Không đủ dữ liệu để tinh chỉnh.")
    space = space or {}
    k_min, k_max = space.get("k_min", 2), min(space.get("k_max", 10), len(X) - 1)
    n_inits = space.get("n_init", [10])
    rows = []
    for k, n_init in product(range(k_min, k_max + 1), n_inits):
        km = KMeans(n_clusters=k, n_init=n_init, random_state=seed)
        lbl = km.fit_predict(X)
        if len(set(lbl)) < 2:
            continue
        sil = float(silhouette_score(X, lbl))
        db = float(davies_bouldin_score(X, lbl))
        ch = float(calinski_harabasz_score(X, lbl))
        crit = {"silhouette": sil, "davies_bouldin": -db, "calinski_harabasz": ch}.get(criterion, sil)
        rows.append({"k": k, "n_init": n_init, "silhouette": round(sil, 4),
                     "davies_bouldin": round(db, 4), "calinski_harabasz": round(ch, 1),
                     "criterion_score": round(float(crit), 4)})
    lb = pd.DataFrame(rows)
    if lb.empty:
        return TuneResult("kmeans", criterion, note="Không phân cụm được.")
    best_row = lb.sort_values("criterion_score", ascending=False).iloc[0]
    best = {"k_selection": "manual", "manual_k": int(best_row["k"]),
            "n_init": int(best_row["n_init"])}
    current = {"k_selection": cfg.get("kmeans", {}).get("k_selection"),
               "manual_k": cfg.get("kmeans", {}).get("manual_k")}
    return TuneResult("kmeans", criterion,
                      leaderboard=lb.sort_values("criterion_score", ascending=False).reset_index(drop=True),
                      best=best, current=current, n_samples=int(X.shape[0]),
                      note=f"Tối ưu k theo {criterion}.")


# --------------------------------------------------------------------------- #
# Persist / apply
# --------------------------------------------------------------------------- #
def apply_tuned(isolation_forest: dict | None = None, kmeans: dict | None = None,
                ts: str | None = None) -> dict:
    """Persist tuned hyperparameters so ``effective_model_config`` applies them."""
    import yaml
    payload = {"applied": True, "tuned_at": ts or datetime.now().isoformat(timespec="seconds")}
    if isolation_forest:
        payload["isolation_forest"] = isolation_forest
    if kmeans:
        payload["kmeans"] = kmeans
    TUNED_PATH.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
                          encoding="utf-8")
    LOG.info("Applied tuned params -> %s", TUNED_PATH.name)
    return payload


def reset_tuned() -> None:
    """Disable tuned overrides (revert to model_config.yaml)."""
    import yaml
    if TUNED_PATH.exists():
        try:
            cur = yaml.safe_load(TUNED_PATH.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            cur = {}
        cur["applied"] = False
        TUNED_PATH.write_text(yaml.safe_dump(cur, allow_unicode=True, sort_keys=False),
                              encoding="utf-8")
        LOG.info("Reset tuned params (applied=false)")


def current_tuned() -> dict:
    import yaml
    if TUNED_PATH.exists():
        try:
            return yaml.safe_load(TUNED_PATH.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            return {}
    return {}


if __name__ == "__main__":
    from pathlib import Path
    from .data_loader import load_all
    from .feature_engineering import build_features
    res = load_all(DATA_ROOT, use_cache=True)
    feats = build_features(res.wide["monthly"], "monthly")
    bm = feats.attrs["base_metrics"]
    iso = tune_isolation_forest(feats, bm)
    print(f"\nIsolation Forest tuning (criterion={iso.criterion}) — top 5:")
    print(iso.leaderboard.head(5).to_string(index=False))
    print("Best:", iso.best, "| current:", iso.current)
    km = tune_kmeans(feats, bm)
    print(f"\nK-means tuning — top 5:")
    print(km.leaderboard.head(5).to_string(index=False))
    print("Best:", km.best)
