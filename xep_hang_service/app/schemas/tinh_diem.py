from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class KiemTraTinhDiemRequest(BaseModel):
    bo_tieu_chi_id: Optional[str] = None
    doi_tuong_id: str
    ky_du_lieu: str

class DuLieuThieuSchema(BaseModel):
    ma_chi_tieu: str
    ma_bien: str
    ten_bien: str

class ChiTieuKhongApDungSchema(BaseModel):
    ma_chi_tieu: str
    ly_do: str

class KiemTraTinhDiemResponse(BaseModel):
    hop_le: bool
    thong_tin: Dict[str, Any]
    loi_cau_hinh: List[Dict[str, Any]] = []
    du_lieu_thieu: List[DuLieuThieuSchema] = []
    chi_tieu_khong_ap_dung: List[ChiTieuKhongApDungSchema] = []

class ThucHienTinhDiemRequest(BaseModel):
    bo_tieu_chi_id: Optional[str] = None
    doi_tuong_id: str
    ky_du_lieu: str
    luu_ket_qua: bool = True
    nguoi_tinh: Optional[str] = "admin"

class KetQuaChiTieuSchema(BaseModel):
    chi_tieu_id: Optional[str] = None
    ma_chi_tieu_goc: str
    ma_chi_tieu_duoc_chon: str
    ten_chi_tieu: Optional[str] = None
    cong_thuc_snapshot: Optional[Dict[str, Any]] = None
    du_lieu_dau_vao: Optional[Dict[str, Any]] = None
    gia_tri_tinh_toan: Optional[float] = None
    diem_thuong: Optional[float] = None
    don_vi_tinh: Optional[str] = "%"
    nguong_da_ap_dung: Optional[Dict[str, Any]] = None
    diem_theo_nguong: Optional[float] = None
    trong_so: Optional[float] = None
    diem_quy_doi: Optional[float] = None
    dien_giai: Optional[str] = None
    trang_thai: str = "DA_TINH"  # DA_TINH, KHONG_AP_DUNG, THIEU_DU_LIEU, LOI_TINH_TOAN

class KetQuaNhomSchema(BaseModel):
    nhom_tieu_chi_id: Optional[str] = None
    ma_nhom: str
    ten_nhom: str
    diem_nhom: float
    diem_dinh_luong: Optional[float] = None
    diem_dinh_tinh: Optional[float] = None
    trong_so_tieu_chi: Optional[float] = None
    trong_so_nhom_dinh_luong: Optional[float] = None
    trong_so_nhom_dinh_tinh: Optional[float] = None
    ket_qua_cac_chi_tieu: List[KetQuaChiTieuSchema] = []

class ThucHienTinhDiemResponse(BaseModel):
    ket_qua_id: str
    bo_tieu_chi_id: Optional[str] = None
    ma_bo_tieu_chi: Optional[str] = None
    phien_ban_bo_tieu_chi: Optional[int] = None
    du_lieu_tinh_diem_id: Optional[str] = None
    doi_tuong: Dict[str, Any]
    ky_du_lieu: str
    tong_diem: float
    xep_hang: Optional[str] = None
    ket_qua_cac_nhom: List[KetQuaNhomSchema] = []
    du_lieu_boc_tach: Optional[List[Dict[str, Any]]] = None
    danh_gia_khoan_7_dieu_20: Optional[Dict[str, Any]] = None
    trang_thai: str = "HOAN_THANH"
    ngay_tinh: Optional[str] = None
    nguoi_tinh: Optional[str] = None
