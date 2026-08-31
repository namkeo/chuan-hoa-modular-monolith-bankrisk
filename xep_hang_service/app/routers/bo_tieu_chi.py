from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas.bo_tieu_chi import BoTieuChiCreate, BoTieuChiUpdate
from app.services.bo_tieu_chi_service import BoTieuChiService
from app.utils.response_utils import format_response

router = APIRouter(prefix="/bo-tieu-chi", tags=["Bộ Tiêu Chí"])
service = BoTieuChiService()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_bo_tieu_chi(data: BoTieuChiCreate):
    res = await service.create(data)
    return format_response(data=res, message="Tạo bộ tiêu chí thành công")

@router.get("/")
async def get_all_bo_tieu_chi(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    is_active: Optional[int] = Query(1)
):
    items = await service.get_all(skip=skip, limit=limit, is_active=is_active)
    return format_response(data=items)

@router.get("/{btc_id}")
async def get_bo_tieu_chi_by_id(btc_id: str):
    res = await service.get_by_id(btc_id)
    return format_response(data=res)

@router.put("/{btc_id}")
async def update_bo_tieu_chi(btc_id: str, data: BoTieuChiUpdate):
    res = await service.update(btc_id, data)
    return format_response(data=res, message="Cập nhật bộ tiêu chí thành công")

@router.delete("/{btc_id}")
async def delete_bo_tieu_chi(btc_id: str):
    await service.delete(btc_id)
    return format_response(message="Xóa bộ tiêu chí thành công")

@router.post("/{btc_id}/cong-bo")
async def publish_bo_tieu_chi(btc_id: str):
    res = await service.publish(btc_id)
    return format_response(data=res, message="Công bố bộ tiêu chí thành công")
