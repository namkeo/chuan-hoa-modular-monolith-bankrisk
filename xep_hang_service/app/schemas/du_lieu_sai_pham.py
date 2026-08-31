from pydantic import BaseModel, Field
from typing import Optional

class DuLieuSaiPhamBase(BaseModel):
    doi_tuong_id: str
    ky_du_lieu: str
    ma_nhom_chi_tieu: str  # "C", "A", "M", "E", "L", "S" hoặc "NTC_C"...
    ma_chi_tieu: Optional[str] = None  # C_DT, A_DT...
    ma_hanh_vi_vi_pham: Optional[str] = None
    noi_dung_chi_tiet: Optional[str] = None
    
    # Nguồn phát hiện
    co_quan_quan_ly_phat_hien: bool = True
    tctd_tu_phat_hien: bool = False
    
    # Thời gian phát hiện & Tình trạng khắc phục
    phat_hien_trong_nam_xep_hang: bool = True
    phat_hien_4_nam_truoc: bool = False
    da_khac_phuc_song: bool = False
    
    # Mức phạt tiền (triệu đồng)
    co_muc_phat_tien: bool = False
    muc_phat_tien_quyet_dinh: Optional[float] = None
    muc_phat_tien_trung_binh: Optional[float] = None
    
    # Số lần vi phạm
    so_lan_vi_pham: int = 1
    is_active: int = 1

class DuLieuSaiPhamCreate(DuLieuSaiPhamBase):
    id: Optional[str] = Field(None, alias="_id")

class DuLieuSaiPhamUpdate(BaseModel):
    ma_nhom_chi_tieu: Optional[str] = None
    ma_chi_tieu: Optional[str] = None
    ma_hanh_vi_vi_pham: Optional[str] = None
    noi_dung_chi_tiet: Optional[str] = None
    co_quan_quan_ly_phat_hien: Optional[bool] = None
    tctd_tu_phat_hien: Optional[bool] = None
    phat_hien_trong_nam_xep_hang: Optional[bool] = None
    phat_hien_4_nam_truoc: Optional[bool] = None
    da_khac_phuc_song: Optional[bool] = None
    co_muc_phat_tien: Optional[bool] = None
    muc_phat_tien_quyet_dinh: Optional[float] = None
    muc_phat_tien_trung_binh: Optional[float] = None
    so_lan_vi_pham: Optional[int] = None
    is_active: Optional[int] = None

class DuLieuSaiPhamResponse(DuLieuSaiPhamBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
