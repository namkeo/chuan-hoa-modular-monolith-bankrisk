"""Kiểm tra và nạp dữ liệu cho module giám sát rủi ro nếu còn trống.

    docker compose exec -T bank_risk_service python /app/scripts/seed_if_empty.py

Chỉ phụ trách module ``giam_sat_rui_ro``. Module xếp hạng tự nạp dữ liệu của mình,
trong container của mình — ``run_web.bat`` gọi cả hai:

    docker compose exec -T xep_hang_service python scripts/seed_if_empty.py

Tệp này KHÔNG tự mở MongoDB. Trước đây nó tự đếm bản ghi trong ``api_payloads``,
``raw_panel_data``, ``risk_scores`` và với tay sang ``xep_hang_service`` bằng
``sys.path`` — xem V2 và V6 trong docs/architecture/data-ownership.md. Nay mọi thứ đi
qua API công khai của từng module.
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


def seed_minio() -> None:
    """MinIO được mount read-only thẳng từ thư mục data/ — chỉ báo cáo, không nạp."""
    print("\n[2/2] Kiểm tra MinIO Object Storage...")
    for folder, bucket in (("bank_risk_data", "bankrisk-files"),
                           ("xep_hang_data", "xep_hang_tctd")):
        path = PROJECT_ROOT / "data" / folder
        if path.exists():
            print(f"  [✓] Bucket '{bucket}': {len(list(path.glob('*')))} tệp "
                  f"mount trực tiếp từ data/{folder}.")
        else:
            print(f"  [!] Không thấy thư mục data/{folder}.")


def main() -> int:
    print("=" * 60)
    print("   KIỂM TRA VÀ NẠP DỮ LIỆU CHO MONGODB & MINIO")
    print("=" * 60)

    print(f"\n[1/2] Module '{api.MODULE_NAME}' ({api.DATABASE})...")
    status = api.health()
    if not status.get("mongo_connected"):
        print(f"  [!] Không kết nối được MongoDB: {status.get('error')}")
        return 1

    force = "--force" in sys.argv
    result = api.seed_if_empty(force=force)
    if result.get("skipped"):
        counts = ", ".join(f"{k}={v}" for k, v in result.get("counts", {}).items())
        print(f"  [✓] Đã có dữ liệu ({counts}) — bỏ qua.")
    elif result.get("seeded"):
        print("  [✓] Đã nạp xong.")
    else:
        print("  [!] Nạp xong nhưng dữ liệu vẫn chưa đủ để phục vụ.")
        return 1

    print("\n  [i] credit_scoring_db do module xếp hạng tự nạp "
          "(xep_hang_service/scripts/seed_if_empty.py) — bỏ qua ở đây.")

    seed_minio()
    print("\n[✓] Hoàn tất kiểm tra và nạp dữ liệu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
