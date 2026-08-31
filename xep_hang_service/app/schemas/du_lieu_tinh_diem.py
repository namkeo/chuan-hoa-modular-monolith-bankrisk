from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class SaiPhamItemSchema(BaseModel):
    ma_nhom_chi_tieu: str  # C, A, M, E, L, S hoặc NTC_C...
    ma_hanh_vi_vi_pham: Optional[str] = None
    noi_dung_chi_tiet: Optional[str] = None
    co_quan_quan_ly_phat_hien: bool = True
    tctd_tu_phat_hien: bool = False
    phat_hien_trong_nam_xep_hang: bool = True
    phat_hien_4_nam_truoc: bool = False
    da_khac_phuc_song: bool = False
    co_muc_phat_tien: bool = False
    muc_phat_tien_quyet_dinh: Optional[float] = None
    muc_phat_tien_trung_binh: Optional[float] = None
    so_lan_vi_pham: int = 1

class DuLieuTinhDiemBase(BaseModel):
    doi_tuong_id: str
    ky_du_lieu: str
    phien_ban: int = 1
    ma_loai_doi_tuong: str
    thuoc_tinh: Dict[str, Any] = {}
    du_lieu: Dict[str, Any] = {}
    danh_sach_sai_pham: Optional[List[Dict[str, Any]]] = []
    trang_thai: str = "DA_PHE_DUYET"  # DA_PHE_DUYET, CHO_PHE_DUYET, NHAP
    nguoi_nhap: Optional[str] = None
    ngay_nhap: Optional[str] = None
    nguoi_phe_duyet: Optional[str] = None
    ngay_phe_duyet: Optional[str] = None
    is_active: int = 1

class DuLieuTinhDiemCreate(DuLieuTinhDiemBase):
    id: Optional[str] = Field(None, alias="_id")

class DuLieuTinhDiemUpdate(BaseModel):
    ma_loai_doi_tuong: Optional[str] = None
    thuoc_tinh: Optional[Dict[str, Any]] = None
    du_lieu: Optional[Dict[str, Any]] = None
    trang_thai: Optional[str] = None
    nguoi_phe_duyet: Optional[str] = None
    ngay_phe_duyet: Optional[str] = None
    is_active: Optional[int] = None

class DuLieuTinhDiemResponse(DuLieuTinhDiemBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
