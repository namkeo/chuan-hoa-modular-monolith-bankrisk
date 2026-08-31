from pydantic import BaseModel, Field
from typing import Optional

class NhomTieuChiBase(BaseModel):
    bo_tieu_chi_id: str
    ma_nhom: str
    so_thu_tu: int
    ten_nhom: str
    trong_so_tieu_chi: float
    trong_so_nhom_dinh_luong: float
    thu_tu_hien_thi: int
    ghi_chu: Optional[str] = None
    is_active: int = 1

class NhomTieuChiCreate(NhomTieuChiBase):
    id: Optional[str] = Field(None, alias="_id")

class NhomTieuChiUpdate(BaseModel):
    ma_nhom: Optional[str] = None
    so_thu_tu: Optional[int] = None
    ten_nhom: Optional[str] = None
    trong_so_tieu_chi: Optional[float] = None
    trong_so_nhom_dinh_luong: Optional[float] = None
    thu_tu_hien_thi: Optional[int] = None
    ghi_chu: Optional[str] = None
    is_active: Optional[int] = None

class NhomTieuChiResponse(NhomTieuChiBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
