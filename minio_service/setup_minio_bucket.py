"""Python script to populate MinIO storage with all bank data files & regulatory PDFs

from DATA_ROOT (d:/Văn bản KTNN/Rủi ro vốn/[SBV] Tài liệu khảo sát/dataset/data_all).
"""
from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ALL_DIR = PROJECT_ROOT.parent / "data_all"
if not DATA_ALL_DIR.exists():
    DATA_ALL_DIR = PROJECT_ROOT

MINIO_STORAGE_DIR = PROJECT_ROOT / "minio_data" / "bankrisk-files"
MINIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

print(f"[+] DATA_ROOT located at: {DATA_ALL_DIR}")
print(f"[+] Syncing files to MinIO Bucket directory: {MINIO_STORAGE_DIR}")

count = 0
for ext in ("*.xlsx", "*.xls", "*.csv", "*.pdf", "*.PDF"):
    for file_path in DATA_ALL_DIR.glob(ext):
        if file_path.name.startswith("~$"):
            continue
        dst = MINIO_STORAGE_DIR / file_path.name
        shutil.copy2(file_path, dst)
        count += 1

# Sync 31 ranking files from Xếp hạng TCTD into dedicated subfolder
xh_dir = PROJECT_ROOT / "Xếp hạng TCTD"
if xh_dir.exists():
    target_sub = MINIO_STORAGE_DIR / "xep_hang_tctd"
    target_sub.mkdir(parents=True, exist_ok=True)
    for f in xh_dir.glob("*.xlsx"):
        if not f.name.startswith("~$"):
            shutil.copy2(f, target_sub / f.name)
            count += 1

print(f"[+] Successfully synced {count} bank Excel, PDF, & Xếp hạng TCTD files to MinIO bucket 'bankrisk-files'!")
