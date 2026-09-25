"""Nạp lại toàn bộ dữ liệu module giám sát rủi ro vào MongoDB.

    python scripts/import_to_mongodb.py

Phần tính toán và ghi dữ liệu nằm TRONG module, tại
``bank_risk_service/src/db_seed.py``; tệp này chỉ là lớp gọi mỏng qua API công khai
``bank_risk_service.api``. Trước đây toàn bộ 280 dòng logic nằm ở đây — ngoài module
nhưng lại tự ghi 21 collection của module (V2 trong
docs/architecture/data-ownership.md).
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from bank_risk_service import api


def main() -> int:
    print(f"Nạp lại dữ liệu module '{api.MODULE_NAME}' -> {api.DATABASE}")
    api.rebuild_all()
    if not api.is_seeded():
        print("[!] Chạy xong nhưng cơ sở dữ liệu vẫn chưa đủ dữ liệu để phục vụ.")
        return 1
    print("[✓] Hoàn tất.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
