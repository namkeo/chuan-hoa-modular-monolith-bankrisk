from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict

class BienSchema(BaseModel):
    ma_bien: str
    ten_bien: str
    bat_buoc: bool = True

class MucDiemSchema(BaseModel):
    thu_tu: Optional[int] = None
    diem: float
    tu: Optional[float] = None
    bao_gom_tu: bool = False
    den: Optional[float] = None
    bao_gom_den: bool = False

class CauHinhTheoDoiTuongSchema(BaseModel):
    ma_loai_doi_tuong: str
    ten_loai_doi_tuong: Optional[str] = None
    trong_so: float
    cac_muc_diem: List[MucDiemSchema] = []

class DieuKienApDungSchema(BaseModel):
    kieu: str = "LUON_DUNG"  # LUON_DUNG, SO_SANH
    truong: Optional[str] = None
    phep_so_sanh: Optional[str] = None  # BANG, KHAC, LON_HON, LON_HON_HOAC_BANG, NHO_HON, NHO_HON_HOAC_BANG, TRONG_DANH_SACH, KHONG_TRONG_DANH_SACH
    gia_tri: Optional[Any] = None

class ChiTieuBase(BaseModel):
    bo_tieu_chi_id: str
    nhom_tieu_chi_id: str
    ma_chi_tieu: str
    ma_chi_tieu_goc: str
    ten_chi_tieu: str
    mo_ta_cong_thuc: Optional[str] = None
    cong_thuc: Dict[str, Any]
    danh_sach_bien: List[BienSchema] = []
    don_vi_tinh: Optional[str] = "%"
    loai_chi_tieu: str = "DINH_LUONG"  # DINH_LUONG, DINH_TINH
    dieu_kien_ap_dung: DieuKienApDungSchema = DieuKienApDungSchema(kieu="LUON_DUNG")
    cau_hinh_theo_doi_tuong: List[CauHinhTheoDoiTuongSchema] = []
    noi_dung_cham_diem: Optional[str] = None
    can_cu_phap_ly: Optional[str] = None
    thu_tu_hien_thi: int = 1
    is_active: int = 1

class ChiTieuCreate(ChiTieuBase):
    id: Optional[str] = Field(None, alias="_id")

class ChiTieuUpdate(BaseModel):
    nhom_tieu_chi_id: Optional[str] = None
    ma_chi_tieu: Optional[str] = None
    ma_chi_tieu_goc: Optional[str] = None
    ten_chi_tieu: Optional[str] = None
    mo_ta_cong_thuc: Optional[str] = None
    cong_thuc: Optional[Dict[str, Any]] = None
    danh_sach_bien: Optional[List[BienSchema]] = None
    don_vi_tinh: Optional[str] = None
    loai_chi_tieu: Optional[str] = None
    dieu_kien_ap_dung: Optional[DieuKienApDungSchema] = None
    cau_hinh_theo_doi_tuong: Optional[List[CauHinhTheoDoiTuongSchema]] = None
    noi_dung_cham_diem: Optional[str] = None
    can_cu_phap_ly: Optional[str] = None
    thu_tu_hien_thi: Optional[int] = None
    is_active: Optional[int] = None

class ChiTieuResponse(ChiTieuBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
