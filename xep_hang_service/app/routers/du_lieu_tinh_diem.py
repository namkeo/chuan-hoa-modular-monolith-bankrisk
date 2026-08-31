from fastapi import APIRouter, Query, status
from typing import Optional
from app.schemas.du_lieu_tinh_diem import DuLieuTinhDiemCreate, DuLieuTinhDiemUpdate
from app.services.du_lieu_tinh_diem_service import DuLieuTinhDiemService
from app.utils.response_utils import format_response

router = APIRouter(prefix="/du-lieu-tinh-diem", tags=["Dữ Liệu Tính Điểm"])
service = DuLieuTinhDiemService()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_du_lieu_tinh_diem(data: DuLieuTinhDiemCreate):
    res = await service.create(data)
    return format_response(data=res, message="Tạo dữ liệu tính điểm thành công")

@router.get("/")
async def get_all_du_lieu_tinh_diem(
    doi_tuong_id: Optional[str] = Query(None),
    ky_du_lieu: Optional[str] = Query(None),
    trang_thai: Optional[str] = Query(None),
    is_active: Optional[int] = Query(1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1)
):
    items = await service.get_all(
        doi_tuong_id=doi_tuong_id,
        ky_du_lieu=ky_du_lieu,
        trang_thai=trang_thai,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return format_response(data=items)

@router.get("/chi-so-car-12-thang")
@router.get("/car-12-thang")
async def get_car_12_thang(
    doi_tuong_id: Optional[str] = Query(None, description="ID / Mã Ngân hàng (VD: Vietinbank, ABBank...)"),
    bank_id: Optional[str] = Query(None, description="Mã Ngân hàng (Ví dụ: Vietinbank, ABBank)"),
    thoi_gian_t: Optional[str] = Query(None, description="Thời điểm t (VD: 2025-12-31, T12/2025). Nếu để trống là thời điểm hiện tại.")
):
    target_bank = doi_tuong_id or bank_id
    if not target_bank:
        return format_response(status_code=400, message="Vui lòng cung cấp doi_tuong_id hoặc bank_id")
    res = await service.get_car_12_thang(doi_tuong_id=target_bank, thoi_gian_t=thoi_gian_t)
    return format_response(data=res, message=f"Lấy chỉ số CAR 12 tháng liên tiếp cho '{target_bank}' thành công")

@router.get("/{dl_id}")
async def get_du_lieu_tinh_diem_by_id(dl_id: str):
    res = await service.get_by_id(dl_id)
    return format_response(data=res)

@router.put("/{dl_id}")
async def update_du_lieu_tinh_diem(dl_id: str, data: DuLieuTinhDiemUpdate):
    res = await service.update(dl_id, data)
    return format_response(data=res, message="Cập nhật dữ liệu tính điểm thành công")

@router.post("/{dl_id}/phe-duyet")
async def approve_du_lieu_tinh_diem(dl_id: str, nguoi_phe_duyet: str = "admin"):
    res = await service.approve(dl_id, nguoi_phe_duyet=nguoi_phe_duyet)
    return format_response(data=res, message="Phê duyệt dữ liệu tính điểm thành công")
