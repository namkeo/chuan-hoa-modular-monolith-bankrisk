from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CanCuPhapLySchema(BaseModel):
    ma_van_ban: str
    ten_van_ban: str

class BoTieuChiBase(BaseModel):
    ma_bo_tieu_chi: str
    ten_bo_tieu_chi: str
    phien_ban: int = 1
    tu_ngay: str
    den_ngay: Optional[str] = None
    trang_thai: str = "DANG_AP_DUNG"
    mo_ta: Optional[str] = None
    can_cu_phap_ly: List[CanCuPhapLySchema] = []
    is_active: int = 1

class BoTieuChiCreate(BoTieuChiBase):
    id: Optional[str] = Field(None, alias="_id")
    nguoi_tao: Optional[str] = "admin"

class BoTieuChiUpdate(BaseModel):
    ten_bo_tieu_chi: Optional[str] = None
    tu_ngay: Optional[str] = None
    den_ngay: Optional[str] = None
    trang_thai: Optional[str] = None
    mo_ta: Optional[str] = None
    can_cu_phap_ly: Optional[List[CanCuPhapLySchema]] = None
    is_active: Optional[int] = None

class BoTieuChiResponse(BoTieuChiBase):
    id: str = Field(..., alias="_id")
    ngay_tao: Optional[str] = None
    nguoi_tao: Optional[str] = None
    ngay_cap_nhat: Optional[str] = None
    nguoi_cap_nhat: Optional[str] = None

    class Config:
        populate_by_name = True
