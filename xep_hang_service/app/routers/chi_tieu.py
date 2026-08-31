from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas.chi_tieu import ChiTieuCreate, ChiTieuUpdate
from app.services.chi_tieu_service import ChiTieuService
from app.utils.response_utils import format_response

router = APIRouter(prefix="/chi-tieu", tags=["Chỉ Tiêu"])
service = ChiTieuService()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_chi_tieu(data: ChiTieuCreate):
    res = await service.create(data)
    return format_response(data=res, message="Tạo chỉ tiêu thành công")

@router.get("/")
async def get_all_chi_tieu(
    bo_tieu_chi_id: Optional[str] = Query(None),
    nhom_tieu_chi_id: Optional[str] = Query(None),
    ma_chi_tieu: Optional[str] = Query(None),
    ma_chi_tieu_goc: Optional[str] = Query(None),
    is_active: Optional[int] = Query(1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1)
):
    items = await service.get_all(
        bo_tieu_chi_id=bo_tieu_chi_id,
        nhom_tieu_chi_id=nhom_tieu_chi_id,
        ma_chi_tieu=ma_chi_tieu,
        ma_chi_tieu_goc=ma_chi_tieu_goc,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return format_response(data=items)

@router.get("/{ct_id}")
async def get_chi_tieu_by_id(ct_id: str):
    res = await service.get_by_id(ct_id)
    return format_response(data=res)

@router.put("/{ct_id}")
async def update_chi_tieu(ct_id: str, data: ChiTieuUpdate):
    res = await service.update(ct_id, data)
    return format_response(data=res, message="Cập nhật chỉ tiêu thành công")

@router.delete("/{ct_id}")
async def delete_chi_tieu(ct_id: str):
    await service.delete(ct_id)
    return format_response(message="Xóa chỉ tiêu thành công")

@router.post("/{ct_id}/kiem-tra")
async def validate_chi_tieu(ct_id: str):
    res = await service.validate_chi_tieu(ct_id)
    return format_response(data=res)
