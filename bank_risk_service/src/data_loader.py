"""Data ingestion: scan the project folder, read multi-frequency bank workbooks,
normalize to panel (long) form and build a bank-period wide table for ML.

The SBV workbooks are stored "wide-by-time": rows are CAMELS supervisory metrics,
columns 1..4 are metadata (STT, metric name, unit, CAMELS group), and every column
from the 5th onward is a reporting period. Each workbook has 4 sheets, one per
frequency: Ngày (daily), Tháng (monthly), Quý (quarterly), Năm (yearly).

Nothing about the metric set is hard-coded — labels are resolved through
config/column_mapping.yaml so new files / new labels are handled by config edits.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .utils import (DATA_ROOT, LOG, PROCESSED_DIR, load_config, normalize_label,
                    strip_accents)

DATA_EXTENSIONS = (".xlsx", ".xls", ".csv", ".parquet")

# Canonical panel schema produced by this module.
PANEL_COLUMNS = ["bank_id", "bank_name", "period", "period_ts", "frequency",
                 "camels_group", "metric_name", "metric_label", "unit",
                 "metric_value", "source_file", "source_file_full_path"]


@dataclass
class LoadResult:
    """Container for everything ingestion produces."""
    panel: pd.DataFrame                       # long form
    wide: dict[str, pd.DataFrame] = field(default_factory=dict)  # frequency -> wide table
    files: list[dict] = field(default_factory=list)             # per-file metadata
    unmapped_labels: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Folder scanning
# --------------------------------------------------------------------------- #
def scan_data_files(folder: Path) -> list[Path]:
    """Return data files in `folder` (non-recursive), excluding temp/lock files."""
    files = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in DATA_EXTENSIONS and not p.name.startswith("~$"):
            files.append(p)
    return files


def scan_pdf_files(folder: Path, recursive: bool = True) -> list[Path]:
    """Return regulatory PDF files. Searches the folder and (optionally) parents."""
    seen: dict[str, Path] = {}
    search_dirs = [folder]
    if recursive:
        search_dirs += [folder.parent, folder.parent.parent]
    for d in search_dirs:
        if not d.exists():
            continue
        for p in d.glob("*.pdf"):
            seen.setdefault(p.name.lower(), p)
        for p in d.glob("*.PDF"):
            seen.setdefault(p.name.lower(), p)
    return sorted(seen.values())


# --------------------------------------------------------------------------- #
# Bank id / name from filename
# --------------------------------------------------------------------------- #
def bank_from_filename(path: Path) -> tuple[str, str]:
    """('ACB_data.xlsx') -> ('ACB', 'ACB'). Strips common suffixes."""
    stem = path.stem
    stem = re.sub(r"[_\- ]*(data|du lieu|dữ liệu)$", "", stem, flags=re.IGNORECASE).strip("_- ")
    bank_id = strip_accents(stem).upper().replace(" ", "")
    return bank_id or path.stem, stem or path.stem


# --------------------------------------------------------------------------- #
# Period parsing
# --------------------------------------------------------------------------- #
_MONTH_RE = re.compile(r"^t\s*0?(\d{1,2})[/\-\. ]+(\d{4})$", re.IGNORECASE)
_QUARTER_RE = re.compile(r"^q\s*([1-4])[/\-\. ]+(\d{4})$", re.IGNORECASE)
_DATE_RE = re.compile(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$")
_YEAR_RE = re.compile(r"(\d{4})")


def parse_period(label, frequency: str):
    """Parse a column header into (period_str, period_timestamp).

    Returns (None, None) when the header is not a recognizable period.
    """
    if label is None:
        return None, None
    if isinstance(label, (pd.Timestamp,)) or hasattr(label, "year"):
        ts = pd.Timestamp(label)
        return _period_str_from_ts(ts, frequency), ts
    s = strip_accents(str(label)).strip()
    if not s:
        return None, None

    m = _DATE_RE.match(s)
    if m:
        d, mo, y = map(int, m.groups())
        try:
            ts = pd.Timestamp(year=y, month=mo, day=d)
            return _period_str_from_ts(ts, frequency or "daily"), ts
        except ValueError:
            return None, None
    m = _MONTH_RE.match(s)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
        ts = pd.Timestamp(year=y, month=mo, day=1) + pd.offsets.MonthEnd(0)
        return f"{y}-{mo:02d}", ts
    m = _QUARTER_RE.match(s)
    if m:
        q, y = int(m.group(1)), int(m.group(2))
        ts = pd.Timestamp(year=y, month=q * 3, day=1) + pd.offsets.MonthEnd(0)
        return f"{y}Q{q}", ts
    # Year-only (e.g. "2023", "Năm 2023")
    if frequency == "yearly" or re.fullmatch(r"(nam\s*)?\d{4}", s):
        m = _YEAR_RE.search(s)
        if m:
            y = int(m.group(1))
            return str(y), pd.Timestamp(year=y, month=12, day=31)
    return None, None


def _period_str_from_ts(ts: pd.Timestamp, frequency: str) -> str:
    if frequency == "daily":
        return ts.strftime("%Y-%m-%d")
    if frequency == "monthly":
        return f"{ts.year}-{ts.month:02d}"
    if frequency == "quarterly":
        return f"{ts.year}Q{(ts.month - 1) // 3 + 1}"
    return str(ts.year)


# --------------------------------------------------------------------------- #
# Metric label -> canonical name
# --------------------------------------------------------------------------- #
def build_alias_lookup(mapping_cfg: dict) -> dict[str, str]:
    """normalized alias label -> canonical metric name."""
    lookup: dict[str, str] = {}
    for canonical, aliases in mapping_cfg.get("metric_aliases", {}).items():
        for alias in aliases:
            lookup[normalize_label(alias)] = canonical
    return lookup


def metric_label_lookup(panel: pd.DataFrame,
                        mapping_cfg: dict | None = None) -> dict[str, dict]:
    """canonical metric name -> nhãn chỉ tiêu gốc (đúng như trong file Excel).

    Ưu tiên nhãn thực sự đọc được từ dữ liệu (nhãn phổ biến nhất khi nhiều file
    dùng cách viết khác nhau), kèm đơn vị & nhóm CAMELS. Chỉ tiêu do code tự tính
    (vd roa suy ra từ lợi nhuận/tổng tài sản) không có trong panel -> lấy alias đầu
    tiên trong column_mapping và đánh dấu is_derived_ratio.
    """
    out: dict[str, dict] = {}
    if panel is not None and not panel.empty and "metric_label" in panel.columns:
        sub = panel.dropna(subset=["metric_label"])
        for name, grp in sub.groupby("metric_name"):
            labels = grp["metric_label"].astype(str)
            mode = labels.mode()
            out[str(name)] = {
                "label": (mode.iloc[0] if not mode.empty else str(name)),
                "unit": _first_str(grp.get("unit")),
                "camels_group": _first_str(grp.get("camels_group")),
                "is_derived_ratio": False,
            }
    for canonical, aliases in (mapping_cfg or {}).get("metric_aliases", {}).items():
        if canonical not in out and aliases:
            out[canonical] = {"label": aliases[0], "unit": None,
                              "camels_group": None, "is_derived_ratio": True}
    return out


def _first_str(s) -> str | None:
    if s is None:
        return None
    vals = s.dropna().astype(str)
    return vals.iloc[0] if not vals.empty else None


ID_COLS = {"bank_id", "bank_name", "period", "period_ts"}

# Cột do feature engineering sinh ra ở cấp hệ thống — không phải chỉ tiêu báo cáo.
ENGINEERED_COLS = {"systemic_stress_index", "systemic_stress_pct",
                   "high_risk_period_flag"}


def missing_metric_table(features: pd.DataFrame, panel: pd.DataFrame,
                         mapping_cfg: dict | None = None) -> pd.DataFrame:
    """Bảng CHỈ TIÊU GỐC còn thiếu: nhãn gốc, số kỳ thiếu, tỷ lệ thiếu.

    Mỗi chỉ tiêu gốc sinh ra ~10 biến phái sinh (``__qoq``, ``__yoy``, ``__accel``,
    ``__roll_z``…). Chúng là biến thể tính toán của cùng một chỉ tiêu chứ không phải
    chỉ tiêu độc lập, nên bị gộp/loại khỏi bảng để tránh trùng lắp. Biến phái sinh
    vẫn được giữ nguyên trong feature set đưa vào ML.
    """
    if features is None or features.empty:
        return pd.DataFrame()
    if mapping_cfg is None:
        mapping_cfg = load_config("column_mapping")
    labels = metric_label_lookup(panel, mapping_cfg)
    n_total = len(features)
    rows = []
    for c in features.columns:
        if (c in ID_COLS or "__" in c or c in ENGINEERED_COLS
                or not pd.api.types.is_numeric_dtype(features[c])):
            continue
        n_missing = int(features[c].isna().sum())
        if n_missing == 0:
            continue
        info = labels.get(c, {})
        rows.append({
            "metric": c,
            "label": info.get("label") or c,
            "unit": info.get("unit"),
            "camels_group": info.get("camels_group"),
            "is_derived_ratio": bool(info.get("is_derived_ratio", False)),
            "n_missing": n_missing,
            "n_total": n_total,
            "missing_pct": round(n_missing / n_total * 100, 2) if n_total else None,
        })
    if not rows:
        return pd.DataFrame()
    return (pd.DataFrame(rows)
            .sort_values(["missing_pct", "label"], ascending=[False, True])
            .reset_index(drop=True))


def frequency_from_sheet(sheet_name: str, freq_map: dict) -> str | None:
    norm = normalize_label(sheet_name)
    for key, freq in freq_map.items():
        if normalize_label(key) in norm:
            return freq
    return None


# --------------------------------------------------------------------------- #
# Single-sheet parsing
# --------------------------------------------------------------------------- #
def _find_header_row(df: pd.DataFrame, keywords: list[str]) -> int | None:
    norm_keywords = [normalize_label(k) for k in keywords]
    for i in range(min(15, len(df))):
        row_text = " ".join(normalize_label(v) for v in df.iloc[i].tolist())
        if any(k in row_text for k in norm_keywords):
            return i
    return None


def parse_sheet(raw: pd.DataFrame, sheet_name: str, frequency: str,
                bank_id: str, bank_name: str, source_file: str,
                source_file_full_path: str, mapping_cfg: dict,
                alias_lookup: dict, unmapped: dict) -> pd.DataFrame:
    """Convert one wide-by-time sheet into panel rows."""
    layout = mapping_cfg.get("layout", {})
    header_idx = _find_header_row(raw, layout.get("header_keywords", ["Nhóm chỉ tiêu", "STT"]))
    if header_idx is None:
        LOG.warning("No header row found in sheet '%s' of %s", sheet_name, source_file)
        return pd.DataFrame(columns=PANEL_COLUMNS)

    header = raw.iloc[header_idx].tolist()

    # Identify metadata columns by keyword on the header.
    def find_col(keys):
        for j, h in enumerate(header):
            hn = normalize_label(h)
            if any(normalize_label(k) in hn for k in keys):
                return j
        return None

    name_col = find_col(layout.get("metric_name_keywords", ["Nhóm chỉ tiêu", "Chỉ tiêu"]))
    unit_col = find_col(layout.get("unit_keywords", ["Đơn vị"]))
    camels_col = find_col(layout.get("camels_keywords", ["Khung CAMELS", "CAMELS"]))
    if name_col is None:
        name_col = 1  # conventional position

    # Period columns: those whose header parses as a period.
    first_period = max(filter(lambda x: x is not None,
                              [name_col, unit_col, camels_col, 0])) + 1
    period_cols: list[tuple[int, str, pd.Timestamp]] = []
    for j in range(first_period, len(header)):
        pstr, pts = parse_period(header[j], frequency)
        if pstr is not None:
            period_cols.append((j, pstr, pts))
    if not period_cols:
        LOG.warning("No period columns parsed in sheet '%s' of %s", sheet_name, source_file)
        return pd.DataFrame(columns=PANEL_COLUMNS)

    records = []
    for i in range(header_idx + 1, len(raw)):
        row = raw.iloc[i].tolist()
        label = row[name_col] if name_col < len(row) else None
        if label is None or (isinstance(label, float) and np.isnan(label)):
            continue
        label_str = str(label).strip()
        if not label_str:
            continue
        canonical = alias_lookup.get(normalize_label(label_str))
        if canonical is None:
            # Track unmapped non-empty group/section labels for diagnostics.
            unmapped[label_str] = unmapped.get(label_str, 0) + 1
            continue
        unit = row[unit_col] if (unit_col is not None and unit_col < len(row)) else None
        camels = row[camels_col] if (camels_col is not None and camels_col < len(row)) else None
        for j, pstr, pts in period_cols:
            if j >= len(row):
                continue
            val = row[j]
            if val is None or (isinstance(val, str) and not val.strip()):
                continue
            num = pd.to_numeric(str(val).replace(",", "").replace("%", "").strip(),
                                errors="coerce") if not isinstance(val, (int, float)) else val
            if num is None or (isinstance(num, float) and np.isnan(num)):
                continue
            records.append({
                "bank_id": bank_id, "bank_name": bank_name,
                "period": pstr, "period_ts": pts, "frequency": frequency,
                "camels_group": (str(camels).strip() if camels is not None
                                 and not (isinstance(camels, float) and np.isnan(camels)) else None),
                "metric_name": canonical, "metric_label": label_str,
                "unit": (str(unit).strip() if unit is not None
                         and not (isinstance(unit, float) and np.isnan(unit)) else None),
                "metric_value": float(num), "source_file": source_file,
                "source_file_full_path": source_file_full_path,
            })
    return pd.DataFrame.from_records(records, columns=PANEL_COLUMNS)


# --------------------------------------------------------------------------- #
# Workbook / file loading
# --------------------------------------------------------------------------- #
def load_workbook(path: Path, mapping_cfg: dict, alias_lookup: dict,
                  unmapped: dict) -> pd.DataFrame:
    """Read every sheet of an Excel workbook into panel form."""
    bank_id, bank_name = bank_from_filename(path)
    freq_map = mapping_cfg.get("frequency_by_sheet", {})
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    try:
        xls = pd.read_excel(path, sheet_name=None, header=None, engine=engine)
    except Exception as exc:  # noqa: BLE001
        LOG.error("Failed to read %s: %s", path.name, exc)
        return pd.DataFrame(columns=PANEL_COLUMNS)

    source_file = f"bankrisk-files/{path.name}"
    source_file_full_path = str(path.resolve().as_posix())

    frames = []
    for sheet_name, raw in xls.items():
        frequency = frequency_from_sheet(sheet_name, freq_map)
        if frequency is None:
            LOG.info("Sheet '%s' in %s has unknown frequency — skipped", sheet_name, path.name)
            continue
        frames.append(parse_sheet(raw, sheet_name, frequency, bank_id, bank_name,
                                  source_file, source_file_full_path, mapping_cfg, alias_lookup, unmapped))
    if not frames:
        return pd.DataFrame(columns=PANEL_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def load_flat_file(path: Path, mapping_cfg: dict, alias_lookup: dict) -> pd.DataFrame:
    """Read an already-tidy csv/parquet. Expected to contain at least
    bank/period/metric columns or canonical metric columns per row."""
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    if set(["bank_id", "period", "metric_name", "metric_value"]).issubset(df.columns):
        df = df.copy()
        for col in PANEL_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df["source_file"] = f"bankrisk-files/{path.name}"
        df["source_file_full_path"] = str(path.resolve().as_posix())
        return df[PANEL_COLUMNS]
    LOG.warning("Flat file %s does not match expected panel schema — skipped", path.name)
    return pd.DataFrame(columns=PANEL_COLUMNS)


# --------------------------------------------------------------------------- #
# Wide table
# --------------------------------------------------------------------------- #
def build_wide_tables(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One wide table per frequency: index (bank_id, bank_name, period, period_ts),
    columns = canonical metric names, values = metric_value (last on duplicates)."""
    wide: dict[str, pd.DataFrame] = {}
    if panel.empty:
        return wide
    for freq, sub in panel.groupby("frequency"):
        pivot = (sub.pivot_table(index=["bank_id", "bank_name", "period", "period_ts"],
                                 columns="metric_name", values="metric_value",
                                 aggfunc="last")
                 .reset_index()
                 .sort_values(["bank_id", "period_ts"]))
        pivot.columns.name = None
        wide[freq] = pivot
    return wide


# --------------------------------------------------------------------------- #
# Caching
# --------------------------------------------------------------------------- #
def _folder_signature(files: list[Path]) -> str:
    h = hashlib.md5()
    for p in files:
        st = p.stat()
        h.update(p.name.encode())
        h.update(str(st.st_mtime_ns).encode())
        h.update(str(st.st_size).encode())
    return h.hexdigest()[:12]


def load_all(folder: Path, use_cache: bool = True, progress=None) -> LoadResult:
    """Top-level ingestion entry point.

    `progress` is an optional callable(fraction: float, message: str) used by the
    Streamlit UI to show a progress bar.
    """
    mapping_cfg = load_config("column_mapping")
    alias_lookup = build_alias_lookup(mapping_cfg)
    files = scan_data_files(folder)
    if not files:
        LOG.warning("No data files found in %s, checking MongoDB 'raw_panel_data'...", folder)
        try:
            import os
            import pymongo
            uri = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27018/")
            client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = client[os.getenv("MONGO_DB", "bank_risk_db")]
            docs = list(db["raw_panel_data"].find({}, {"_id": 0}))
            if docs:
                panel = pd.DataFrame(docs)
                LOG.info("Successfully loaded %d panel records from MongoDB 'raw_panel_data'", len(panel))
                unmapped = {}
                if "period_ts" in panel.columns:
                    panel["period_ts"] = pd.to_datetime(panel["period_ts"], errors="coerce")
                if "metric_value" in panel.columns:
                    panel["metric_value"] = pd.to_numeric(panel["metric_value"], errors="coerce")
                wide = build_wide_tables(panel)
                try:
                    from .multi_frequency import build_combined_wide
                    mf_cfg = load_config("model_config")
                    if mf_cfg.get("multi_frequency", {}).get("enabled", True):
                        combined = build_combined_wide(wide, mf_cfg)
                        if combined is not None and not combined.empty:
                            wide["combined"] = combined
                except Exception as exc:
                    LOG.warning("Could not build combined table: %s", exc)
                return LoadResult(panel=panel, wide=wide, files=[], unmapped_labels=unmapped)
        except Exception as exc:
            LOG.warning("MongoDB raw_panel_data fallback failed: %s", exc)
        return LoadResult(panel=pd.DataFrame(columns=PANEL_COLUMNS))

    sig = _folder_signature(files)
    cache_panel = PROCESSED_DIR / f"panel_{sig}.parquet"
    if use_cache and cache_panel.exists():
        LOG.info("Loading panel from cache %s", cache_panel.name)
        panel = pd.read_parquet(cache_panel)
        unmapped: dict[str, int] = {}
    else:
        unmapped = {}
        frames = []
        n = len(files)
        for idx, path in enumerate(files):
            if progress:
                progress(idx / n, f"Đang đọc {path.name}")
            LOG.info("Reading %s (%d/%d)", path.name, idx + 1, n)
            if path.suffix.lower() in (".xlsx", ".xls"):
                frames.append(load_workbook(path, mapping_cfg, alias_lookup, unmapped))
            else:
                frames.append(load_flat_file(path, mapping_cfg, alias_lookup))
        panel = (pd.concat(frames, ignore_index=True)
                 if frames else pd.DataFrame(columns=PANEL_COLUMNS))
        if not panel.empty:
            panel = panel.drop_duplicates(
                subset=["bank_id", "period", "frequency", "metric_name"], keep="last")
            try:
                panel.to_parquet(cache_panel, index=False)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Could not cache panel: %s", exc)
        if progress:
            progress(1.0, "Hoàn tất đọc dữ liệu")

    # Normalize dtypes. Building the panel from per-row dicts (or reading it back
    # from parquet) can leave columns as object dtype holding Python objects. That
    # breaks the `.dt` accessor on period_ts (validation gap-detection, feature
    # engineering, multi-freq) and, for metric_value, forces element-wise Python
    # arithmetic that raises ZeroDivisionError on pct_change instead of yielding
    # inf/NaN. Coerce to real datetime64 / float64 so all downstream numeric ops
    # (and the pivoted wide/feature tables) behave.
    if not panel.empty:
        if "period_ts" in panel.columns:
            panel["period_ts"] = pd.to_datetime(panel["period_ts"], errors="coerce")
        if "metric_value" in panel.columns:
            panel["metric_value"] = pd.to_numeric(panel["metric_value"], errors="coerce")

    wide = build_wide_tables(panel)

    # Cross-frequency integration: a monthly-grain table enriched with as-of
    # quarterly + yearly metrics, exposed as the "combined" frequency.
    try:
        from .multi_frequency import build_combined_wide
        mf_cfg = load_config("model_config")
        if mf_cfg.get("multi_frequency", {}).get("enabled", True):
            combined = build_combined_wide(wide, mf_cfg)
            if combined is not None and not combined.empty:
                wide["combined"] = combined
    except Exception as exc:  # noqa: BLE001
        LOG.warning("Could not build combined multi-frequency table: %s", exc)

    file_meta = []
    for path in files:
        bid, bname = bank_from_filename(path)
        minio_file = f"bankrisk-files/{path.name}"
        sub = panel[panel["source_file"] == minio_file] if not panel.empty else panel
        file_meta.append({
            "file": minio_file,
            "filename": path.name,
            "source_file_full_path": str(path.resolve().as_posix()),
            "bank_id": bid, "bank_name": bname,
            "rows": int(len(sub)),
            "frequencies": sorted(sub["frequency"].dropna().unique().tolist()) if not sub.empty else [],
            "metrics": int(sub["metric_name"].nunique()) if not sub.empty else 0,
            "size_kb": round(path.stat().st_size / 1024, 1),
        })
    return LoadResult(panel=panel, wide=wide, files=file_meta,
                      unmapped_labels=dict(sorted(unmapped.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    res = load_all(DATA_ROOT, use_cache=False)
    print(f"Panel rows: {len(res.panel)}")
    print(f"Banks: {res.panel['bank_id'].nunique() if not res.panel.empty else 0}")
    for f, w in res.wide.items():
        print(f"  {f}: {w.shape[0]} bank-periods x {w.shape[1]} cols")
    if res.unmapped_labels:
        print("Unmapped labels (top 10):")
        for k, v in list(res.unmapped_labels.items())[:10]:
            print(f"   {v:3d}  {k}")
