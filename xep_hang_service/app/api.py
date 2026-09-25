"""API công khai của module **xep_hang_tctd** — cửa duy nhất đi vào từ bên ngoài.

    from app import api
    await api.seed_if_empty()

Mọi thành phần ngoài module chỉ được dùng những gì khai báo trong ``__all__``. KHÔNG
được import ``xep_hang_service.app.*`` từ ngoài, và KHÔNG được truy vấn trực tiếp các
collection của ``credit_scoring_db`` (``BoTieuChi``, ``NhomTieuChi``, ``ChiTieu``,
``DoiTuongDanhGia``, ``DuLieuTinhDiem``, ``DuLieuSaiPham``, ``KetQuaTinhDiem``) — xem
``docs/architecture/data-ownership.yml``.

Tầng web trước đây đọc thẳng ``KetQuaTinhDiem`` và ``DoiTuongDanhGia`` (V1, đã xử lý
ở bước 2); ``scripts/seed_if_empty.py`` ở thư mục gốc thì với tay vào đây bằng
``sys.path`` từ một container không có mã của module (V6, đã xử lý). Tệp này là nơi
ranh giới đó được tuyên bố thành văn.

Hàm bất đồng bộ vì module dùng driver Motor. Bên trong tự mở và đóng kết nối, nên gọi
được từ script một lần chạy mà không cần lo vòng đời kết nối.
"""
from __future__ import annotations

from typing import Any

__all__ = [
    "DATABASE",
    "MODULE_NAME",
    "count_results",
    "get_lich_su",
    "health",
    "is_seeded",
    "list_doi_tuong",
    "recalculate_all",
    "seed_if_empty",
]

MODULE_NAME = "xep_hang_tctd"
DATABASE = "credit_scoring_db"


class _Session:
    """Mở kết nối MongoDB của module trong một khối ``async with``."""

    async def __aenter__(self):
        from app.core.database import connect_to_mongo, get_database
        await connect_to_mongo()
        return get_database()

    async def __aexit__(self, *_exc):
        from app.core.database import close_mongo_connection
        await close_mongo_connection()
        return False


async def count_results() -> int:
    """Số bản ghi kết quả xếp hạng hiện có."""
    async with _Session() as db:
        return await db.KetQuaTinhDiem.count_documents({})


async def is_seeded() -> bool:
    """Module đã có kết quả xếp hạng để phục vụ chưa?"""
    return await count_results() > 0


async def recalculate_all() -> int:
    """Tính lại điểm xếp hạng cho toàn bộ TCTD từ nguồn Excel. Trả về số bản ghi."""
    from scripts.load_all_31_excel_rankings import process_all_rankings
    await process_all_rankings()
    return await count_results()


async def seed_if_empty(force: bool = False) -> dict[str, Any]:
    """Tính lại nếu chưa có dữ liệu. ``{"seeded": bool, "skipped": bool, "count": int}``."""
    existing = await count_results()
    if existing > 0 and not force:
        return {"seeded": True, "skipped": True, "count": existing}
    written = await recalculate_all()
    return {"seeded": written > 0, "skipped": False, "count": written}


async def list_doi_tuong(limit: int = 1000) -> list[dict]:
    """Danh sách TCTD đang hoạt động."""
    from app.repositories.doi_tuong_repository import DoiTuongRepository
    async with _Session():
        return await DoiTuongRepository().find_many({"is_active": 1}, limit=limit)


async def get_lich_su(doi_tuong_id: str, limit: int = 1000) -> list[dict]:
    """Lịch sử điểm xếp hạng của một TCTD qua các kỳ, cũ đến mới."""
    from app.repositories.ket_qua_tinh_diem_repository import KetQuaTinhDiemRepository
    async with _Session():
        return await KetQuaTinhDiemRepository().find_many(
            {"is_active": 1,
             "$or": [{"doi_tuong_id": doi_tuong_id}, {"ma_doi_tuong": doi_tuong_id}]},
            sort=[("ky_du_lieu", 1)], limit=limit)


async def health() -> dict[str, Any]:
    """Trạng thái module: kết nối được MongoDB chưa, đã có dữ liệu chưa."""
    try:
        count = await count_results()
        return {"module": MODULE_NAME, "database": DATABASE,
                "mongo_connected": True, "seeded": count > 0, "count": count}
    except Exception as exc:  # noqa: BLE001
        return {"module": MODULE_NAME, "database": DATABASE,
                "mongo_connected": False, "seeded": False, "error": str(exc)}
