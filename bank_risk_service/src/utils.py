"""Shared utilities: paths, config loading, logging, text normalization, caching.

Everything routes through the project root so the package works no matter what the
current working directory is when Streamlit / the CLI launches it.
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
# PROJECT_ROOT = where the CODE lives (this package's parent). All generated
# artifacts (cache, models, outputs) are written here.
SERVICE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent
CONFIG_DIR = (
    (SERVICE_ROOT / "config")
    if (SERVICE_ROOT / "config").exists()
    else (PROJECT_ROOT / "config")
    if (PROJECT_ROOT / "config").exists()
    else (PROJECT_ROOT / "web" / "config")
)
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FEEDBACK_DIR = DATA_DIR / "feedback"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
CHARTS_DIR = OUTPUTS_DIR / "charts"
EXPORTS_DIR = OUTPUTS_DIR / "exports"

for _d in (RAW_DIR, PROCESSED_DIR, FEEDBACK_DIR, MODELS_DIR, REPORTS_DIR, CHARTS_DIR, EXPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# DATA_ROOT = where the BANK INPUT files (.xlsx/.csv + regulatory PDFs) live.
# It can differ from PROJECT_ROOT (e.g. running the code from "source_code" while
# the data sits in a sibling "data_all"). Resolution order:
#   1. env var BANKRISK_DATA_DIR
#   2. config/data_dir.txt  (a single line with the folder path)
#   3. PROJECT_ROOT itself, if it already contains data files
#   4. a sibling/known folder that contains data files (e.g. ../data_all)
#   5. fall back to PROJECT_ROOT
# --------------------------------------------------------------------------- #
_DATA_EXTS = (".xlsx", ".xls", ".csv", ".parquet")


def _has_data_files(folder: Path) -> bool:
    try:
        return any(p.suffix.lower() in _DATA_EXTS and not p.name.startswith("~$")
                   for p in folder.iterdir() if p.is_file())
    except (OSError, FileNotFoundError):
        return False


def resolve_data_dir() -> Path:
    """Locate the folder holding the bank input files (see order above)."""
    env = os.environ.get("BANKRISK_DATA_DIR")
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()

    cfg_file = CONFIG_DIR / "data_dir.txt"
    if cfg_file.exists():
        try:
            p = Path(cfg_file.read_text(encoding="utf-8").strip()).expanduser()
            if p.exists():
                return p.resolve()
        except OSError:
            pass

    # 1. Search sibling data_all / data folders first (which contain all bank files)
    candidates = [
        PROJECT_ROOT.parent / "data_all",
        PROJECT_ROOT.parent / "data",
        PROJECT_ROOT.with_name("data_all"),
    ]
    for c in candidates:
        if c.exists() and _has_data_files(c):
            return c.resolve()

    if _has_data_files(PROJECT_ROOT):
        return PROJECT_ROOT

    # Scan immediate siblings for any folder containing data files.
    try:
        siblings = [d for d in PROJECT_ROOT.parent.iterdir() if d.is_dir()]
        for c in siblings:
            if c.exists() and c.resolve() != PROJECT_ROOT and _has_data_files(c):
                return c.resolve()
    except (OSError, FileNotFoundError):
        pass

    return PROJECT_ROOT


DATA_ROOT = resolve_data_dir()


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def get_logger(name: str = "bankrisk", level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger (idempotent — safe to call repeatedly)."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                                datefmt="%H:%M:%S")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False
    return logger


LOG = get_logger()


# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def load_config(name: str) -> dict[str, Any]:
    """Load a YAML config file from config/ by basename (with or without .yaml)."""
    fname = name if name.endswith((".yaml", ".yml")) else f"{name}.yaml"
    path = CONFIG_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` into a copy of ``base``."""
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def effective_model_config() -> dict[str, Any]:
    """Model config with tuned hyperparameters (config/tuned_params.yaml) overlaid.

    Fine-tuning writes ``tuned_params.yaml`` with ``applied: true`` and overrides for
    ``isolation_forest`` / ``kmeans``. When present and applied, those take effect for
    every model run; otherwise the base ``model_config.yaml`` is used unchanged.
    NOT cached so a freshly-applied tuning is picked up on the next pipeline run.
    """
    base = dict(load_config("model_config"))
    tuned_path = CONFIG_DIR / "tuned_params.yaml"
    if tuned_path.exists():
        try:
            with tuned_path.open("r", encoding="utf-8") as fh:
                tuned = yaml.safe_load(fh) or {}
            if tuned.get("applied"):
                overrides = {k: tuned[k] for k in ("isolation_forest", "kmeans")
                             if k in tuned}
                merged = _deep_merge(base, overrides)
                merged["_tuned_applied"] = True
                merged["_tuned_at"] = tuned.get("tuned_at")
                return merged
        except Exception:  # noqa: BLE001
            pass
    return base


# --------------------------------------------------------------------------- #
# Text normalization (accent / case / whitespace tolerant matching)
# --------------------------------------------------------------------------- #
def strip_accents(text: str) -> str:
    """Remove Vietnamese diacritics for fuzzy matching."""
    if not isinstance(text, str):
        return ""
    # Normalize đ/Đ which NFD does not decompose.
    text = text.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def normalize_label(text: Any) -> str:
    """Lower-case, de-accent, collapse whitespace — canonical form for label matching."""
    if text is None:
        return ""
    s = strip_accents(str(text)).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def safe_div(numerator: float, denominator: float) -> float | None:
    """Division that returns None on zero / invalid denominator."""
    try:
        if denominator in (0, None) or denominator != denominator:  # NaN check
            return None
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return None
