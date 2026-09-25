"""Nạp dữ liệu xếp hạng nếu cơ sở dữ liệu của module còn trống.

Chạy BÊN TRONG container xep_hang_service, nơi có sẵn mã của module và nguồn Excel:

    docker compose exec -T xep_hang_service python scripts/seed_if_empty.py

Trước đây việc này do ``scripts/seed_if_empty.py`` ở thư mục gốc đảm nhiệm, chạy trong
container bank_risk_service và với tay sang đây bằng ``sys.path.insert``. Container đó
không chứa mã của module nên lệnh import luôn hỏng, script nuốt lỗi rồi in ra "seeding
complete" — cơ sở dữ liệu trống rỗng mà quy trình khởi động vẫn báo thành công (V6
trong docs/architecture/data-ownership.md).

Mỗi module tự nạp dữ liệu của mình, bằng mã của mình, trong container của mình. Tệp này
đi qua API công khai ``xep_hang_service.api`` chứ không chạm vào collection.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import api

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("seed_xep_hang")


def _excel_files() -> list[Path]:
    from scripts.load_all_31_excel_rankings import EXCEL_FOLDER
    folder = Path(EXCEL_FOLDER)
    return sorted(folder.glob("XH_TCTD_*.xlsx")) if folder.exists() else []


async def main() -> int:
    status = await api.health()
    if not status.get("mongo_connected"):
        log.error("Không kết nối được MongoDB: %s", status.get("error"))
        return 1

    if status.get("seeded"):
        log.info("credit_scoring_db đã có %d bản ghi KetQuaTinhDiem — bỏ qua.",
                 status["count"])
        return 0

    files = _excel_files()
    if not files:
        # Thất bại ở đây phải dừng hẳn. Báo "thành công" khi không nạp được gì chính
        # là lỗi mà tệp này sinh ra để sửa.
        from scripts.load_all_31_excel_rankings import EXCEL_FOLDER
        log.error("Không tìm thấy tệp XH_TCTD_*.xlsx nào trong '%s'. "
                  "Kiểm tra mount ./data:/app/data:ro trong docker-compose.yml.",
                  EXCEL_FOLDER)
        return 1

    log.info("credit_scoring_db trống — tính điểm xếp hạng từ %d tệp Excel.", len(files))
    result = await api.seed_if_empty()
    if not result.get("seeded"):
        log.error("Đã chạy tính điểm nhưng KetQuaTinhDiem vẫn trống.")
        return 1

    log.info("Hoàn tất: %d bản ghi KetQuaTinhDiem.", result["count"])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
