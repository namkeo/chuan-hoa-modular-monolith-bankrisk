from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas.nhom_tieu_chi import NhomTieuChiCreate, NhomTieuChiUpdate
from app.services.nhom_tieu_chi_service import NhomTieuChiService
from app.utils.response_utils import format_response

router = APIRouter(prefix="/nhom-tieu-chi", tags=["Nhóm Tiêu Chí"])
service = NhomTieuChiService()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_nhom_tieu_chi(data: NhomTieuChiCreate):
    res = await service.create(data)
    return format_response(data=res, message="Tạo nhóm tiêu chí thành công")

@router.get("/")
async def get_all_nhom_tieu_chi(
    bo_tieu_chi_id: Optional[str] = Query(None),
    ma_nhom: Optional[str] = Query(None),
    is_active: Optional[int] = Query(1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1)
):
    items = await service.get_all(
        bo_tieu_chi_id=bo_tieu_chi_id,
        ma_nhom=ma_nhom,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return format_response(data=items)

@router.get("/{ntc_id}")
async def get_nhom_tieu_chi_by_id(ntc_id: str):
    res = await service.get_by_id(ntc_id)
    return format_response(data=res)

@router.put("/{ntc_id}")
async def update_nhom_tieu_chi(ntc_id: str, data: NhomTieuChiUpdate):
    res = await service.update(ntc_id, data)
    return format_response(data=res, message="Cập nhật nhóm tiêu chí thành công")

@router.delete("/{ntc_id}")
async def delete_nhom_tieu_chi(ntc_id: str):
    await service.delete(ntc_id)
    return format_response(message="Xóa nhóm tiêu chí thành công")
