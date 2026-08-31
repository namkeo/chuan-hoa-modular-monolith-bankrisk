from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas.doi_tuong_danh_gia import DoiTuongDanhGiaCreate, DoiTuongDanhGiaUpdate
from app.repositories.doi_tuong_repository import DoiTuongRepository
from app.core.exceptions import NotFoundException
from app.utils.response_utils import format_response

router = APIRouter(prefix="/doi-tuong-danh-gia", tags=["Đối Tượng Đánh Giá"])
repo = DoiTuongRepository()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_doi_tuong(data: DoiTuongDanhGiaCreate):
    doc = data.model_dump(by_alias=True)
    if not doc.get("_id"):
        doc["_id"] = data.ma_doi_tuong
    res = await repo.create(doc)
    return format_response(data=res, message="Tạo đối tượng đánh giá thành công")

import json, logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _get_precomputed_fallback():
    fpath = Path(__file__).resolve().parent.parent.parent / "scripts" / "precomputed_31_rankings.json"
    if fpath.exists():
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading precomputed fallback JSON: {e}")
    return []

@router.get("/")
async def get_all_doi_tuong(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    is_active: Optional[int] = Query(1)
):
    query = {}
    if is_active is not None:
        query["is_active"] = is_active
    try:
        items = await repo.find_many(query, skip=skip, limit=limit)
    except Exception as e:
        logger.warning(f"MongoDB unavailable ({e}), using precomputed fallback for get_all_doi_tuong")
        fallback = _get_precomputed_fallback()
        seen = set()
        items = []
        for item in fallback:
            dt_id = item.get("doi_tuong_id") or item.get("ma_doi_tuong")
            if dt_id and dt_id not in seen:
                seen.add(dt_id)
                items.append({
                    "_id": dt_id,
                    "doi_tuong_id": dt_id,
                    "ma_doi_tuong": item.get("ma_doi_tuong", dt_id),
                    "ten_doi_tuong": item.get("ten_doi_tuong", dt_id),
                    "ten_viet_tat": item.get("ten_viet_tat", dt_id),
                    "ma_loai_doi_tuong": item.get("ma_loai_doi_tuong", "NHTM_QUY_MO_LON"),
                    "is_active": 1
                })
        items = items[skip : skip + limit]

    return format_response(data=items)

@router.get("/{dt_id}")
async def get_doi_tuong_by_id(dt_id: str):
    res = None
    try:
        res = await repo.get_by_id(dt_id)
        if not res:
            res = await repo.get_by_code(dt_id)
    except Exception as e:
        logger.warning(f"MongoDB unavailable ({e}), using precomputed fallback for doi_tuong {dt_id}")
        fallback = _get_precomputed_fallback()
        match = next((i for i in fallback if i.get("doi_tuong_id") == dt_id or i.get("ma_doi_tuong") == dt_id), None)
        if match:
            res = {
                "_id": match.get("doi_tuong_id") or match.get("ma_doi_tuong"),
                "doi_tuong_id": match.get("doi_tuong_id"),
                "ma_doi_tuong": match.get("ma_doi_tuong"),
                "ten_doi_tuong": match.get("ten_doi_tuong"),
                "ten_viet_tat": match.get("ten_viet_tat"),
                "ma_loai_doi_tuong": match.get("ma_loai_doi_tuong", "NHTM_QUY_MO_LON"),
                "is_active": 1
            }

    if not res:
        raise NotFoundException(f"Không tìm thấy đối tượng: {dt_id}")
    return format_response(data=res)

@router.put("/{dt_id}")
async def update_doi_tuong(dt_id: str, data: DoiTuongDanhGiaUpdate):
    existing = await repo.get_by_id(dt_id)
    if not existing:
        raise NotFoundException(f"Không tìm thấy đối tượng: {dt_id}")
    res = await repo.update(dt_id, data.model_dump(exclude_unset=True))
    return format_response(data=res, message="Cập nhật đối tượng thành công")

@router.delete("/{dt_id}")
async def delete_doi_tuong(dt_id: str):
    res = await repo.soft_delete(dt_id)
    return format_response(message="Xóa đối tượng thành công")
