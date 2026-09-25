"""API công khai của module **giam_sat_rui_ro** — cửa duy nhất đi vào từ bên ngoài.

Mọi thành phần ngoài module (script vận hành cấp gốc, cổng web, module khác) chỉ được
dùng những gì khai báo trong ``__all__`` dưới đây:

    from bank_risk_service import api
    if not api.is_seeded():
        api.rebuild_all()

KHÔNG được import ``bank_risk_service.src.*`` từ ngoài, và KHÔNG được truy vấn trực
tiếp các collection của ``bank_risk_db``. Danh sách collection module này sở hữu nằm
trong ``docs/architecture/data-ownership.yml``; vi phạm bị bắt bởi
``scripts/audit/check_data_ownership.py``.

Vì sao cần tệp này: trước đây ``scripts/import_to_mongodb.py`` nằm ngoài module nhưng
import sâu vào ``src.*`` và tự ghi 21 collection, còn ``scripts/seed_if_empty.py`` tự
mở MongoDB để đếm bản ghi. Không có ranh giới nào, nên mọi thứ đều là nội bộ của mọi
thứ (V2 trong docs/architecture/data-ownership.md).

Đây là bước 3/6 của lộ trình Modular Monolith: tuyên bố bề mặt công khai. Bên trong
vẫn giữ nguyên cấu trúc cũ — việc chia lại theo năng lực là bước 5.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = [
    "DATABASE",
    "MODULE_NAME",
    "available_frequencies",
    "get_payload",
    "health",
    "is_seeded",
    "rebuild_all",
    "rebuild_frequency",
    "seed_if_empty",
]

MODULE_NAME = "giam_sat_rui_ro"
DATABASE = "bank_risk_db"

# Bộ ba collection tối thiểu phải có dữ liệu để coi là đã nạp xong: một payload hợp
# lệ để phục vụ API, dữ liệu gốc đã chuẩn hoá, và điểm rủi ro đã chấm.
_SEEDED_REQUIREMENTS = ("api_payloads", "raw_panel_data", "risk_scores")


def _db():
    from .src.db_seed import get_mongo_client
    return get_mongo_client()[DATABASE]


def is_seeded() -> bool:
    """Cơ sở dữ liệu của module đã có đủ dữ liệu để phục vụ chưa?"""
    db = _db()
    if db["api_payloads"].find_one({"empty": False}) is None:
        return False
    return all(db[name].count_documents({}) > 0 for name in _SEEDED_REQUIREMENTS)


def seed_if_empty(force: bool = False) -> dict[str, Any]:
    """Nạp dữ liệu nếu còn trống. Trả về ``{"seeded": bool, "skipped": bool}``.

    ``force=True`` thì luôn tính lại, kể cả khi đã có dữ liệu.
    """
    if not force and is_seeded():
        db = _db()
        counts = {n: db[n].count_documents({}) for n in _SEEDED_REQUIREMENTS}
        return {"seeded": True, "skipped": True, "counts": counts}

    rebuild_all()
    return {"seeded": is_seeded(), "skipped": False}


def rebuild_all() -> None:
    """Chạy lại toàn bộ pipeline cho mọi tần suất và ghi xuống MongoDB + tệp JSON."""
    from .src.db_seed import import_all_to_mongodb
    import_all_to_mongodb()


def rebuild_frequency(frequency: str, use_cache: bool = True) -> Path:
    """Chạy lại pipeline cho một tần suất. Trả về đường dẫn tệp JSON đã ghi."""
    from .src.api_export import export_frequency
    return export_frequency(frequency, use_cache=use_cache)


def available_frequencies() -> list[str]:
    """Các tần suất dữ liệu nguồn hiện có, 'combined' đứng đầu khi khả dụng."""
    from .src.pipeline import available_frequencies as _freqs
    from .src.utils import DATA_ROOT
    return _freqs(DATA_ROOT)


def get_payload(frequency: str) -> dict | None:
    """Payload phân tích của một tần suất, đọc từ MongoDB. None nếu chưa có."""
    doc = _db()["api_payloads"].find_one({"frequency": frequency}, {"_id": 0})
    return doc


def health() -> dict[str, Any]:
    """Trạng thái module: kết nối được MongoDB chưa, đã nạp dữ liệu chưa."""
    try:
        db = _db()
        db.client.admin.command("ping")
        return {
            "module": MODULE_NAME,
            "database": DATABASE,
            "mongo_connected": True,
            "seeded": is_seeded(),
            "collections": len(db.list_collection_names()),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "module": MODULE_NAME,
            "database": DATABASE,
            "mongo_connected": False,
            "seeded": False,
            "error": str(exc),
        }
