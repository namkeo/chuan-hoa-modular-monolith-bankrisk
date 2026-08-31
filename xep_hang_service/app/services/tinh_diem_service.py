import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.repositories.bo_tieu_chi_repository import BoTieuChiRepository
from app.repositories.nhom_tieu_chi_repository import NhomTieuChiRepository
from app.repositories.chi_tieu_repository import ChiTieuRepository
from app.repositories.doi_tuong_repository import DoiTuongRepository
from app.repositories.du_lieu_tinh_diem_repository import DuLieuTinhDiemRepository
from app.repositories.ket_qua_tinh_diem_repository import KetQuaTinhDiemRepository

from app.services.dieu_kien_service import DieuKienService
from app.services.cong_thuc_service import CongThucService
from app.services.nguong_diem_service import NguongDiemService
from app.services.du_lieu_tinh_diem_service import DuLieuTinhDiemService

from app.schemas.tinh_diem import (
    KiemTraTinhDiemResponse,
    ThucHienTinhDiemResponse,
    KetQuaNhomSchema,
    KetQuaChiTieuSchema,
    DuLieuThieuSchema,
    ChiTieuKhongApDungSchema
)
from app.core.exceptions import (
    NotFoundException,
    MissingInputDataException,
    CriteriaConflictException,
    ConfigurationException
)
from app.utils.decimal_utils import to_decimal, round_decimal, decimal_to_float_or_int

from app.repositories.du_lieu_sai_pham_repository import DuLieuSaiPhamRepository

logger = logging.getLogger(__name__)

def get_matching_loai_types(ma_loai: str) -> set:
    aliases = {
        "CN_NGAN_HANG_NUOC_NGOAI": {"CN_NGAN_HANG_NUOC_NGOAI", "CHI_NHANH_NGAN_HANG_NUOC_NGOAI"},
        "CHI_NHANH_NGAN_HANG_NUOC_NGOAI": {"CN_NGAN_HANG_NUOC_NGOAI", "CHI_NHANH_NGAN_HANG_NUOC_NGOAI"},
    }
    res = set(aliases.get(ma_loai, [ma_loai]))
    res.update(["ALL", "*"])
    return res

class TinhDiemService:
    """
    Core Service thực hiện kiểm tra và tính điểm toàn bộ bộ tiêu chí.
    """

    def __init__(
        self,
        bo_tieu_chi_repo: Optional[BoTieuChiRepository] = None,
        nhom_tieu_chi_repo: Optional[NhomTieuChiRepository] = None,
        chi_tieu_repo: Optional[ChiTieuRepository] = None,
        doi_tuong_repo: Optional[DoiTuongRepository] = None,
        du_lieu_tinh_diem_repo: Optional[DuLieuTinhDiemRepository] = None,
        ket_qua_tinh_diem_repo: Optional[KetQuaTinhDiemRepository] = None,
        du_lieu_sai_pham_repo: Optional[DuLieuSaiPhamRepository] = None
    ):
        self.bo_tieu_chi_repo = bo_tieu_chi_repo or BoTieuChiRepository()
        self.nhom_tieu_chi_repo = nhom_tieu_chi_repo or NhomTieuChiRepository()
        self.chi_tieu_repo = chi_tieu_repo or ChiTieuRepository()
        self.doi_tuong_repo = doi_tuong_repo or DoiTuongRepository()
        self.du_lieu_tinh_diem_repo = du_lieu_tinh_diem_repo or DuLieuTinhDiemRepository()
        self.ket_qua_tinh_diem_repo = ket_qua_tinh_diem_repo or KetQuaTinhDiemRepository()
        self.du_lieu_sai_pham_repo = du_lieu_sai_pham_repo or DuLieuSaiPhamRepository()
        self.du_lieu_tinh_diem_service = DuLieuTinhDiemService(repo=self.du_lieu_tinh_diem_repo)

    async def _prepare_context(
        self,
        doi_tuong_id: str,
        ky_du_lieu: str,
        bo_tieu_chi_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bước 1 - 4: Lấy và hợp nhất dữ liệu đầu vào, đối tượng, bộ tiêu chí, nhóm tiêu chí, chỉ tiêu.
        """
        # 1. Lấy dữ liệu tính điểm
        du_lieu_input = await self.du_lieu_tinh_diem_repo.get_input_data(doi_tuong_id, ky_du_lieu)
        if not du_lieu_input:
            raise NotFoundException(
                f"Không tìm thấy dữ liệu tính điểm đã phê duyệt cho đối tượng '{doi_tuong_id}', kỳ '{ky_du_lieu}'"
            )

        # Lấy thông tin đối tượng
        doi_tuong = await self.doi_tuong_repo.get_by_code(doi_tuong_id)
        if not doi_tuong:
            # Fallback nếu dùng _id
            doi_tuong = await self.doi_tuong_repo.get_by_id(doi_tuong_id)

        # Thuộc tính ưu tiên dữ liệu tính điểm trước, sau đó tới đối tượng
        thuoc_tinh_doi_tuong = doi_tuong.get("thuoc_tinh", {}) if doi_tuong else {}
        thuoc_tinh_du_lieu = du_lieu_input.get("thuoc_tinh", {})
        thuoc_tinh = {**thuoc_tinh_doi_tuong, **thuoc_tinh_du_lieu}

        ma_loai_doi_tuong = du_lieu_input.get(
            "ma_loai_doi_tuong",
            doi_tuong.get("ma_loai_doi_tuong") if doi_tuong else ""
        )

        # 2. Xác định bộ tiêu chí
        if bo_tieu_chi_id:
            bo_tieu_chi = await self.bo_tieu_chi_repo.get_by_id(bo_tieu_chi_id)
        else:
            bo_tieu_chi = await self.bo_tieu_chi_repo.get_active_bo_tieu_chi()

        if not bo_tieu_chi:
            raise NotFoundException("Không tìm thấy bộ tiêu chí áp dụng")

        btc_id = bo_tieu_chi["_id"]

        # 3. Lấy nhóm tiêu chí
        nhom_list = await self.nhom_tieu_chi_repo.get_by_bo_tieu_chi(btc_id, only_active=True)

        # 4. Lấy chỉ tiêu
        chi_tieu_list = await self.chi_tieu_repo.get_by_bo_tieu_chi(btc_id, only_active=True)

        return {
            "du_lieu_input": du_lieu_input,
            "doi_tuong": doi_tuong or {
                "ma_doi_tuong": doi_tuong_id,
                "ten_doi_tuong": doi_tuong_id,
                "ma_loai_doi_tuong": ma_loai_doi_tuong
            },
            "thuoc_tinh": thuoc_tinh,
            "ma_loai_doi_tuong": ma_loai_doi_tuong,
            "bo_tieu_chi": bo_tieu_chi,
            "nhom_list": nhom_list,
            "chi_tieu_list": chi_tieu_list
        }

    async def kiem_tra_truoc_khi_tinh(
        self,
        doi_tuong_id: str,
        ky_du_lieu: str,
        bo_tieu_chi_id: Optional[str] = None
    ) -> KiemTraTinhDiemResponse:
        """
        API validation: Kiểm tra dữ liệu thiếu, xung đột phương án, hoặc cấu hình không áp dụng.
        """
        ctx = await self._prepare_context(doi_tuong_id, ky_du_lieu, bo_tieu_chi_id)
        du_lieu_dict = ctx["du_lieu_input"].get("du_lieu", {})
        thuoc_tinh = ctx["thuoc_tinh"]
        ma_loai_doi_tuong = ctx["ma_loai_doi_tuong"]

        loi_cau_hinh = []
        du_lieu_thieu = []
        chi_tieu_khong_ap_dung = []

        # 5. Nhóm chỉ tiêu theo ma_chi_tieu_goc
        grouped_chi_tieu: Dict[str, List[Dict[str, Any]]] = {}
        for ct in ctx["chi_tieu_list"]:
            goc = ct.get("ma_chi_tieu_goc", ct.get("ma_chi_tieu"))
            grouped_chi_tieu.setdefault(goc, []).append(ct)

        # 6 - 8. Kiểm tra từng nhóm chỉ tiêu gốc
        for goc, items in grouped_chi_tieu.items():
            # Filter thỏa điều kiện áp dụng
            matching = [
                ct for ct in items
                if DieuKienService.kiem_tra_dieu_kien(ct.get("dieu_kien_ap_dung"), thuoc_tinh)
            ]

            if len(matching) == 0:
                for ct in items:
                    chi_tieu_khong_ap_dung.append(ChiTieuKhongApDungSchema(
                        ma_chi_tieu=ct.get("ma_chi_tieu"),
                        ly_do="Không thỏa mãn điều kiện áp dụng"
                    ))
                continue
            elif len(matching) > 1:
                loi_cau_hinh.append({
                    "ma_loi": "XUNG_DOT_PHUONG_AN",
                    "ma_chi_tieu_goc": goc,
                    "danh_sach_chi_tieu": [ct.get("ma_chi_tieu") for ct in matching],
                    "message": f"Có {len(matching)} chỉ tiêu cùng thỏa mãn điều kiện áp dụng cho mã gốc '{goc}'"
                })
                continue

            selected_ct = matching[0]
            ma_ct = selected_ct.get("ma_chi_tieu")

            # 7. Tìm cấu hình theo loai_doi_tuong
            cau_hinh_list = selected_ct.get("cau_hinh_theo_doi_tuong", [])
            valid_types = get_matching_loai_types(ma_loai_doi_tuong)
            matched_cfg = [c for c in cau_hinh_list if c.get("ma_loai_doi_tuong") in valid_types]

            if not matched_cfg:
                chi_tieu_khong_ap_dung.append(ChiTieuKhongApDungSchema(
                    ma_chi_tieu=ma_ct,
                    ly_do="Không có cấu hình cho loại đối tượng"
                ))
                continue

            # 8. Kiểm tra biến đầu vào (chỉ áp dụng cho định lượng)
            if selected_ct.get("loai_chi_tieu") != "DINH_TUYNH":
                for bien in selected_ct.get("danh_sach_bien", []):
                    ma_bien = bien.get("ma_bien")
                    bat_buoc = bien.get("bat_buoc", True)
                    val = self.resolve_metric_val(du_lieu_dict, ma_ct, ma_bien)
                    if bat_buoc and val is None:
                        du_lieu_thieu.append(DuLieuThieuSchema(
                            ma_chi_tieu=ma_ct,
                            ma_bien=ma_bien,
                            ten_bien=bien.get("ten_bien", ma_bien)
                        ))

        hop_le = (len(loi_cau_hinh) == 0 and len(du_lieu_thieu) == 0)

        return KiemTraTinhDiemResponse(
            hop_le=hop_le,
            thong_tin={
                "bo_tieu_chi_id": ctx["bo_tieu_chi"]["_id"],
                "doi_tuong_id": doi_tuong_id,
                "ky_du_lieu": ky_du_lieu,
                "ma_loai_doi_tuong": ma_loai_doi_tuong
            },
            loi_cau_hinh=loi_cau_hinh,
            du_lieu_thieu=du_lieu_thieu,
            chi_tieu_khong_ap_dung=chi_tieu_khong_ap_dung
        )

    async def thuc_hien_tinh_diem(
        self,
        doi_tuong_id: str,
        ky_du_lieu: str,
        bo_tieu_chi_id: Optional[str] = None,
        luu_ket_qua: bool = True,
        nguoi_tinh: str = "admin"
    ) -> ThucHienTinhDiemResponse:
        """
        Thực hiện tính điểm toàn bộ tiêu chí cho 1 đối tượng trong kỳ.
        """
        logger.info(f"Bắt đầu tính điểm cho đối tượng '{doi_tuong_id}', kỳ '{ky_du_lieu}'...")
        ctx = await self._prepare_context(doi_tuong_id, ky_du_lieu, bo_tieu_chi_id)

        du_lieu_input = ctx["du_lieu_input"]
        du_lieu_dict = du_lieu_input.get("du_lieu", {})
        thuoc_tinh = ctx["thuoc_tinh"]
        ma_loai_doi_tuong = ctx["ma_loai_doi_tuong"]
        bo_tieu_chi = ctx["bo_tieu_chi"]

        ket_qua_nhom_list: List[KetQuaNhomSchema] = []

        # Lặp qua từng nhóm tiêu chí (NhomTieuChi)
        for nhom in ctx["nhom_list"]:
            nhom_id = nhom["_id"]
            ma_nhom = nhom["ma_nhom"]
            ten_nhom = nhom["ten_nhom"]
            ts_tieu_chi = to_decimal(nhom.get("trong_so_tieu_chi", 0))
            ts_dinh_luong = to_decimal(nhom.get("trong_so_nhom_dinh_luong", 0))
            ts_dinh_tinh = ts_tieu_chi - ts_dinh_luong if ts_tieu_chi >= ts_dinh_luong else Decimal("0")

            # Lấy danh sách các chỉ tiêu thuộc nhóm này
            chi_tieu_in_nhom = [
                ct for ct in ctx["chi_tieu_list"]
                if ct.get("nhom_tieu_chi_id") == nhom_id
            ]

            # Nhóm theo ma_chi_tieu_goc trong nhóm này
            grouped_in_nhom: Dict[str, List[Dict[str, Any]]] = {}
            for ct in chi_tieu_in_nhom:
                goc = ct.get("ma_chi_tieu_goc", ct.get("ma_chi_tieu"))
                grouped_in_nhom.setdefault(goc, []).append(ct)

            ket_qua_chi_tieu_list: List[KetQuaChiTieuSchema] = []
            tong_diem_quy_doi_dinh_luong = Decimal("0")
            tong_diem_quy_doi_dinh_tinh = Decimal("0")
            has_dinh_luong = False
            has_dinh_tinh = False

            for goc, items in grouped_in_nhom.items():
                # 6. Chọn chỉ tiêu thỏa mãn điều kiện áp dụng
                matching = [
                    ct for ct in items
                    if DieuKienService.kiem_tra_dieu_kien(ct.get("dieu_kien_ap_dung"), thuoc_tinh)
                ]

                if len(matching) == 0:
                    continue
                elif len(matching) > 1:
                    danh_sach = [ct.get("ma_chi_tieu") for ct in matching]
                    raise CriteriaConflictException(ma_chi_tieu_goc=goc, danh_sach_chi_tieu=danh_sach)

                selected_ct = matching[0]
                ma_ct = selected_ct.get("ma_chi_tieu")
                ten_ct = selected_ct.get("ten_chi_tieu")

                # 7. Tìm cấu hình theo loai_doi_tuong
                cau_hinh_list = selected_ct.get("cau_hinh_theo_doi_tuong", [])
                valid_types = get_matching_loai_types(ma_loai_doi_tuong)
                matched_cfg = [c for c in cau_hinh_list if c.get("ma_loai_doi_tuong") in valid_types]

                if not matched_cfg:
                    # KHONG_AP_DUNG
                    ket_qua_chi_tieu_list.append(KetQuaChiTieuSchema(
                        chi_tieu_id=selected_ct["_id"],
                        ma_chi_tieu_goc=goc,
                        ma_chi_tieu_duoc_chon=ma_ct,
                        ten_chi_tieu=ten_ct,
                        trang_thai="KHONG_AP_DUNG",
                        dien_giai="Không có cấu hình cho loại đối tượng"
                    ))
                    continue

                cfg = matched_cfg[0]
                trong_so = to_decimal(cfg.get("trong_so", 0))

                is_dinh_tuynh = (selected_ct.get("loai_chi_tieu") == "DINH_TUYNH") or (not selected_ct.get("cong_thuc"))

                if is_dinh_tuynh:
                    # Tính điểm định tính cho nhóm chỉ tiêu từ collection DuLieuSaiPham theo Khoản 3 Điều 16a TT52 / TT23
                    val_dec, dien_giai, dt_details = await self.tinh_diem_dinh_tinh_nhom(
                        doi_tuong_id=doi_tuong_id,
                        ky_du_lieu=ky_du_lieu,
                        ma_nhom=ma_nhom,
                        du_lieu_input=du_lieu_input,
                        du_lieu_dict=du_lieu_dict
                    )
                    diem_theo_nguong_dec = val_dec
                    muc_diem = None
                    gia_tri_dec_rounded = val_dec
                    du_lieu_dau_vao = dt_details
                    has_dinh_tinh = True
                else:
                    danh_sach_bien = selected_ct.get("danh_sach_bien", [])
                    missing_vars = []
                    du_lieu_dau_vao = {}
                    for bien in danh_sach_bien:
                        ma_b = bien.get("ma_bien")
                        val = self.resolve_metric_val(du_lieu_dict, ma_ct, ma_b)
                        if val is not None:
                            du_lieu_dau_vao[ma_b] = val
                            du_lieu_dict[ma_b] = val
                        elif bien.get("bat_buoc", True):
                            missing_vars.append(ma_b)

                    if missing_vars:
                        raise MissingInputDataException(
                            missing_vars=missing_vars,
                            message=f"Thiếu dữ liệu đầu vào cho chỉ tiêu '{ma_ct}' ({missing_vars})"
                        )

                    try:
                        gia_tri_dec = CongThucService.tinh_bieu_thuc(
                            node=selected_ct.get("cong_thuc", {}),
                            du_lieu=du_lieu_dict,
                            ma_chi_tieu=ma_ct
                        )
                    except Exception:
                        resolved_v = self.resolve_metric_val(du_lieu_dict, ma_ct)
                        gia_tri_dec = to_decimal(resolved_v if resolved_v is not None else 0)
                    gia_tri_dec_rounded = round_decimal(gia_tri_dec, 4)

                    cac_muc_diem = cfg.get("cac_muc_diem", [])
                    muc_diem = NguongDiemService.tim_muc_diem(
                        gia_tri=gia_tri_dec_rounded,
                        cac_muc_diem=cac_muc_diem,
                        ma_chi_tieu=ma_ct
                    )
                    diem_ban_dau_dec = to_decimal(muc_diem.get("diem", 0))

                    diem_thuong_dec = Decimal("0")
                    diem_theo_nguong_dec = diem_ban_dau_dec
                    dien_giai = NguongDiemService.tao_dien_giai(gia_tri_dec_rounded, muc_diem)

                    has_dinh_luong = True

                diem_quy_doi_dec = (diem_theo_nguong_dec * trong_so) / Decimal("100")
                diem_quy_doi_rounded = round_decimal(diem_quy_doi_dec, 4)

                if is_dinh_tuynh:
                    tong_diem_quy_doi_dinh_tinh += diem_quy_doi_rounded
                else:
                    tong_diem_quy_doi_dinh_luong += diem_quy_doi_rounded

                ket_qua_chi_tieu_list.append(KetQuaChiTieuSchema(
                    chi_tieu_id=selected_ct["_id"],
                    ma_chi_tieu_goc=goc,
                    ma_chi_tieu_duoc_chon=ma_ct,
                    ten_chi_tieu=ten_ct,
                    cong_thuc_snapshot={
                        "mo_ta_cong_thuc": selected_ct.get("mo_ta_cong_thuc"),
                        "cong_thuc": selected_ct.get("cong_thuc")
                    },
                    du_lieu_dau_vao=decimal_to_float_or_int(du_lieu_dau_vao),
                    gia_tri_tinh_toan=float(gia_tri_dec_rounded),
                    diem_thuong=float(diem_thuong_dec) if not is_dinh_tuynh and diem_thuong_dec > 0 else None,
                    don_vi_tinh=selected_ct.get("don_vi_tinh", "%"),
                    nguong_da_ap_dung=muc_diem,
                    diem_theo_nguong=float(diem_theo_nguong_dec),
                    trong_so=float(trong_so),
                    diem_quy_doi=float(diem_quy_doi_rounded),
                    dien_giai=dien_giai,
                    trang_thai="DA_TINH"
                ))

            # 12. Tổng hợp điểm nhóm = (diem_dinh_luong * trong_so_dinh_luong / 100) + (diem_dinh_tinh * trong_so_dinh_tinh / 100)
            diem_dl_val = float(round_decimal(tong_diem_quy_doi_dinh_luong, 4)) if has_dinh_luong else None
            diem_dt_val = float(round_decimal(tong_diem_quy_doi_dinh_tinh, 4)) if has_dinh_tinh else None

            dl_dec = tong_diem_quy_doi_dinh_luong if has_dinh_luong else Decimal("0")
            dt_dec = tong_diem_quy_doi_dinh_tinh if has_dinh_tinh else Decimal("0")

            diem_nhom_dec = dl_dec * (ts_dinh_luong / Decimal("100")) + dt_dec * (ts_dinh_tinh / Decimal("100"))
            diem_nhom_rounded = round_decimal(diem_nhom_dec, 4)

            ket_qua_nhom_list.append(KetQuaNhomSchema(
                nhom_tieu_chi_id=nhom_id,
                ma_nhom=ma_nhom,
                ten_nhom=ten_nhom,
                diem_nhom=float(diem_nhom_rounded),
                diem_dinh_luong=diem_dl_val,
                diem_dinh_tinh=diem_dt_val,
                trong_so_tieu_chi=float(ts_tieu_chi),
                trong_so_nhom_dinh_luong=float(ts_dinh_luong),
                trong_so_nhom_dinh_tinh=float(ts_dinh_tinh),
                ket_qua_cac_chi_tieu=ket_qua_chi_tieu_list
            ))

        # 13. Tổng hợp toàn bộ (Tổng điểm & Xếp hạng)
        tong_diem_dec, xep_hang_goc = self.tong_hop_toan_bo(ket_qua_nhom_list)
        tong_diem_rounded = round_decimal(tong_diem_dec, 2)

        # 13b. Đánh giá quy định hạ xếp hạng xuống (E) theo Khoản 7 Điều 20 Thông tư 52
        danh_gia_khoan_7 = await self.kiem_tra_dieu_20_khoan_7(
            doi_tuong_id=doi_tuong_id,
            ky_du_lieu=ky_du_lieu,
            xep_hang_goc=xep_hang_goc,
            tong_diem=float(tong_diem_rounded),
            ket_qua_cac_nhom=ket_qua_nhom_list,
            du_lieu_dict=du_lieu_dict,
            raw_dong_nguon_dict=du_lieu_dict
        )
        xep_hang_cuoi_cung = danh_gia_khoan_7["xep_hang_cuoi_cung"]

        # 14. Lưu KetQuaTinhDiem (nếu luu_ket_qua=True)
        ket_qua_id = f"KQ_{doi_tuong_id}_{ky_du_lieu}"

        doc_ket_qua = {
            "_id": ket_qua_id,
            "bo_tieu_chi_id": bo_tieu_chi["_id"],
            "ma_bo_tieu_chi": bo_tieu_chi.get("ma_bo_tieu_chi"),
            "phien_ban_bo_tieu_chi": bo_tieu_chi.get("phien_ban"),
            "du_lieu_tinh_diem_id": du_lieu_input["_id"],
            "doi_tuong_id": doi_tuong_id,
            "ma_doi_tuong": ctx["doi_tuong"].get("ma_doi_tuong", doi_tuong_id),
            "ten_doi_tuong": ctx["doi_tuong"].get("ten_doi_tuong", doi_tuong_id),
            "ma_loai_doi_tuong": ma_loai_doi_tuong,
            "ky_du_lieu": ky_du_lieu,
            "tong_diem": float(tong_diem_rounded),
            "xep_hang": xep_hang_cuoi_cung,
            "danh_gia_khoan_7_dieu_20": danh_gia_khoan_7,
            "ket_qua_cac_nhom": [nhom.model_dump() for nhom in ket_qua_nhom_list],
            "trang_thai": "HOAN_THANH",
            "ngay_tinh": datetime.now().isoformat(),
            "nguoi_tinh": nguoi_tinh,
            "is_active": 1
        }

        if luu_ket_qua:
            await self.ket_qua_tinh_diem_repo.save_or_update(doc_ket_qua)
            logger.info(f"Đã lưu kết quả tính điểm ID: {ket_qua_id}")

        return ThucHienTinhDiemResponse(
            ket_qua_id=ket_qua_id,
            bo_tieu_chi_id=bo_tieu_chi["_id"],
            ma_bo_tieu_chi=bo_tieu_chi.get("ma_bo_tieu_chi"),
            phien_ban_bo_tieu_chi=bo_tieu_chi.get("phien_ban"),
            du_lieu_tinh_diem_id=du_lieu_input["_id"],
            doi_tuong={
                "ma_doi_tuong": ctx["doi_tuong"].get("ma_doi_tuong", doi_tuong_id),
                "ten_doi_tuong": ctx["doi_tuong"].get("ten_doi_tuong", doi_tuong_id),
                "ma_loai_doi_tuong": ma_loai_doi_tuong
            },
            ky_du_lieu=ky_du_lieu,
            tong_diem=float(tong_diem_rounded),
            xep_hang=xep_hang_cuoi_cung,
            ket_qua_cac_nhom=ket_qua_nhom_list,
            danh_gia_khoan_7_dieu_20=danh_gia_khoan_7,
            trang_thai="HOAN_THANH",
            ngay_tinh=doc_ket_qua["ngay_tinh"],
            nguoi_tinh=nguoi_tinh
        )

    async def thuc_hien_tinh_diem_tu_camels(
        self,
        doi_tuong_id: str,
        ky_du_lieu: str,
        camels_json_data: List[Dict[str, Any]],
        bo_tieu_chi_id: Optional[str] = None
    ) -> ThucHienTinhDiemResponse:
        """
        Thực hiện tính điểm toàn bộ tiêu chí cho 1 đối tượng từ dữ liệu file Excel CAMELS (JSON).
        """
        logger.info(f"Bắt đầu tính điểm từ file Excel CAMELS cho '{doi_tuong_id}', kỳ '{ky_du_lieu}'...")

        try:
            doi_tuong = await self.doi_tuong_repo.get_by_id(doi_tuong_id)
        except Exception:
            doi_tuong = None
        if not doi_tuong:
            try:
                doi_tuong = await self.doi_tuong_repo.get_by_code(doi_tuong_id)
            except Exception:
                doi_tuong = None
        if not doi_tuong:
            doi_tuong = {"_id": doi_tuong_id, "ma_doi_tuong": doi_tuong_id, "ten_doi_tuong": doi_tuong_id, "ma_loai_doi_tuong": "NHTM_QUY_MO_LON"}

        ma_loai_doi_tuong = doi_tuong.get("ma_loai_doi_tuong", "NHTM_QUY_MO_LON")

        bo_tieu_chi = None
        try:
            if not bo_tieu_chi_id:
                bo_tieu_chi = await self.bo_tieu_chi_repo.get_active_bo_tieu_chi()
            else:
                bo_tieu_chi = await self.bo_tieu_chi_repo.get_by_id(bo_tieu_chi_id)
        except Exception as err:
            logger.warn(f"Database query for BoTieuChi failed: {err}")

        nhom_list = []
        chi_tieu_list = []
        if bo_tieu_chi:
            try:
                nhom_list = await self.nhom_tieu_chi_repo.get_by_bo_tieu_chi(bo_tieu_chi["_id"])
                chi_tieu_list = await self.chi_tieu_repo.get_by_bo_tieu_chi(bo_tieu_chi["_id"], only_active=True)
            except Exception as err:
                logger.warn(f"Database query for NhomTieuChi / ChiTieu failed: {err}")

        raw_dong_nguon_dict = {
            item["ma_dong_nguon"]: item.get("so_lieu")
            for item in camels_json_data
            if isinstance(item, dict)
        }
        dong_nguon_dict = {
            k: (v if v is not None else 0)
            for k, v in raw_dong_nguon_dict.items()
        }

        du_lieu_input = {}
        try:
            du_lieu_input = (await self.du_lieu_tinh_diem_repo.get_input_data(doi_tuong_id, ky_du_lieu)) or {}
        except Exception:
            pass
        du_lieu_dict = du_lieu_input.get("du_lieu", {})
        thuoc_tinh = dict(doi_tuong.get("thuoc_tinh", {}))

        if raw_dong_nguon_dict.get("R-105") is not None or raw_dong_nguon_dict.get("R-112") is not None:
            thuoc_tinh["ap_dung_thong_tu_41"] = True
        elif raw_dong_nguon_dict.get("R-102") is not None or raw_dong_nguon_dict.get("R-109") is not None:
            thuoc_tinh["ap_dung_thong_tu_41"] = False
        elif "ap_dung_thong_tu_41" not in thuoc_tinh:
            thuoc_tinh["ap_dung_thong_tu_41"] = True

        ket_qua_nhom_list: List[KetQuaNhomSchema] = []

        for nhom in nhom_list:
            nhom_id = nhom["_id"]
            ma_nhom = nhom["ma_nhom"]
            ten_nhom = nhom["ten_nhom"]
            ts_tieu_chi = to_decimal(nhom.get("trong_so_tieu_chi", 0))
            ts_dinh_luong = to_decimal(nhom.get("trong_so_nhom_dinh_luong", 0))
            ts_dinh_tinh = ts_tieu_chi - ts_dinh_luong if ts_tieu_chi >= ts_dinh_luong else Decimal("0")

            chi_tieu_in_nhom = [ct for ct in chi_tieu_list if ct.get("nhom_tieu_chi_id") == nhom_id]

            grouped_in_nhom: Dict[str, List[Dict[str, Any]]] = {}
            for ct in chi_tieu_in_nhom:
                goc = ct.get("ma_chi_tieu_goc", ct.get("ma_chi_tieu"))
                grouped_in_nhom.setdefault(goc, []).append(ct)

            tong_diem_quy_doi_dinh_luong = Decimal("0")
            tong_diem_quy_doi_dinh_tinh = Decimal("0")
            ket_qua_chi_tieu_list: List[KetQuaChiTieuSchema] = []
            has_dinh_luong = False
            has_dinh_tinh = False

            for goc, items in grouped_in_nhom.items():
                matching = [ct for ct in items if DieuKienService.kiem_tra_dieu_kien(ct.get("dieu_kien_ap_dung"), thuoc_tinh)]
                if not matching:
                    continue

                selected_ct = matching[0]
                ma_ct = selected_ct.get("ma_chi_tieu")
                ten_ct = selected_ct.get("ten_chi_tieu")

                cau_hinh_list = selected_ct.get("cau_hinh_theo_doi_tuong", [])
                valid_types = get_matching_loai_types(ma_loai_doi_tuong)
                matched_cfg = [c for c in cau_hinh_list if c.get("ma_loai_doi_tuong") in valid_types]

                if not matched_cfg:
                    ket_qua_chi_tieu_list.append(KetQuaChiTieuSchema(
                        chi_tieu_id=selected_ct["_id"],
                        ma_chi_tieu_goc=goc,
                        ma_chi_tieu_duoc_chon=ma_ct,
                        ten_chi_tieu=ten_ct,
                        trang_thai="KHONG_AP_DUNG",
                        dien_giai="Không có cấu hình cho loại đối tượng"
                    ))
                    continue

                cfg = matched_cfg[0]
                trong_so = to_decimal(cfg.get("trong_so", 0))
                is_dinh_tuynh = (selected_ct.get("loai_chi_tieu") == "DINH_TUYNH") or (not selected_ct.get("cong_thuc"))

                mota_goc = selected_ct.get("mo_ta_cong_thuc", "")
                bieu_thuc_the_so = ""

                if is_dinh_tuynh:
                    val_dec, dien_giai, dt_details = await self.tinh_diem_dinh_tinh_nhom(
                        doi_tuong_id=doi_tuong_id,
                        ky_du_lieu=ky_du_lieu,
                        ma_nhom=ma_nhom,
                        du_lieu_input=du_lieu_input,
                        du_lieu_dict=du_lieu_dict
                    )
                    diem_theo_nguong_dec = val_dec
                    muc_diem = None
                    gia_tri_dec_rounded = val_dec
                    du_lieu_dau_vao = dt_details
                    has_dinh_tinh = True
                else:
                    cfg_formula = selected_ct.get("cong_thuc_theo_template")
                    du_lieu_dau_vao = {}

                    r105_val = raw_dong_nguon_dict.get("R-105")
                    r102_val = raw_dong_nguon_dict.get("R-102")
                    r112_val = raw_dong_nguon_dict.get("R-112")
                    r109_val = raw_dong_nguon_dict.get("R-109")

                    def _fmt(v):
                        if v is None:
                            return "0"
                        try:
                            fv = float(v)
                            return f"{int(fv):,}" if fv.is_integer() else f"{fv:,.2f}"
                        except Exception:
                            return str(v)

                    if (goc in ["1.1.a", "1.1"] or ma_ct in ["1.1.a", "1.1"]) and (r105_val is not None or r102_val is not None):
                        if r105_val is not None:
                            calc_val = float(r105_val)
                            mota_goc = "Tỷ lệ an toàn vốn theo Thông tư 41 (R-101 = R-105)"
                            r106_v = raw_dong_nguon_dict.get("R-106")
                            r107_v = raw_dong_nguon_dict.get("R-107")
                            if r106_v is not None and r107_v is not None:
                                bieu_thuc_the_so = f"R-101 = R-105 = (R-106 / R-107) × 100 = ({_fmt(r106_v)} / {_fmt(r107_v)}) × 100 = {calc_val:,.3f}%"
                            else:
                                bieu_thuc_the_so = f"R-101 = R-105 = {calc_val:,.3f}%"
                        else:
                            calc_val = float(r102_val)
                            mota_goc = "Tỷ lệ an toàn vốn theo Thông tư 22 (R-101 = R-102)"
                            r103_v = raw_dong_nguon_dict.get("R-103")
                            r104_v = raw_dong_nguon_dict.get("R-104")
                            if r103_v is not None and r104_v is not None:
                                bieu_thuc_the_so = f"R-101 = R-102 = (R-103 / R-104) × 100 = ({_fmt(r103_v)} / {_fmt(r104_v)}) × 100 = {calc_val:,.3f}%"
                            else:
                                bieu_thuc_the_so = f"R-101 = R-102 = {calc_val:,.3f}%"
                        gia_tri_dec = to_decimal(calc_val)
                    elif (goc in ["1.2.a", "1.2"] or ma_ct in ["1.2.a", "1.2"]) and (r112_val is not None or r109_val is not None):
                        if r112_val is not None:
                            calc_val = float(r112_val)
                            mota_goc = "Tỷ lệ an toàn vốn cấp 1 theo Thông tư 41 (R-108 = R-112)"
                            r113_v = raw_dong_nguon_dict.get("R-113")
                            r114_v = raw_dong_nguon_dict.get("R-114")
                            if r113_v is not None and r114_v is not None:
                                bieu_thuc_the_so = f"R-108 = R-112 = (R-113 / R-114) × 100 = ({_fmt(r113_v)} / {_fmt(r114_v)}) × 100 = {calc_val:,.3f}%"
                            else:
                                bieu_thuc_the_so = f"R-108 = R-112 = {calc_val:,.3f}%"
                        else:
                            calc_val = float(r109_val)
                            mota_goc = "Tỷ lệ an toàn vốn cấp 1 theo Thông tư 22 (R-108 = R-109)"
                            r110_v = raw_dong_nguon_dict.get("R-110")
                            r111_v = raw_dong_nguon_dict.get("R-111")
                            if r110_v is not None and r111_v is not None:
                                bieu_thuc_the_so = f"R-108 = R-109 = (R-110 / R-111) × 100 = ({_fmt(r110_v)} / {_fmt(r111_v)}) × 100 = {calc_val:,.3f}%"
                            else:
                                bieu_thuc_the_so = f"R-108 = R-109 = {calc_val:,.3f}%"
                        gia_tri_dec = to_decimal(calc_val)
                    elif cfg_formula:
                        tu_codes = cfg_formula.get("tu_so", [])
                        mau_codes = cfg_formula.get("mau_so", [])
                        phep_tu = cfg_formula.get("phep_tinh_tu_so", "+")
                        he_so = cfg_formula.get("he_so", 100)

                        for c in tu_codes + mau_codes:
                            if c in dong_nguon_dict:
                                du_lieu_dau_vao[c] = dong_nguon_dict[c]

                        if phep_tu == "-" and len(tu_codes) >= 2:
                            tu_val = dong_nguon_dict.get(tu_codes[0], 0) - dong_nguon_dict.get(tu_codes[1], 0)
                        else:
                            tu_val = sum(dong_nguon_dict.get(c, 0) for c in tu_codes if c in dong_nguon_dict)

                        mau_val = sum(dong_nguon_dict.get(c, 0) for c in mau_codes if c in dong_nguon_dict)

                        if len(mau_codes) == 0:
                            calc_val = tu_val * he_so
                        elif mau_val != 0:
                            calc_val = (tu_val / mau_val) * he_so
                        else:
                            calc_val = 0.0

                        gia_tri_dec = to_decimal(calc_val)
                        mota_goc = cfg_formula.get("mota", "")

                        # Construct formula with R codes
                        if phep_tu == "-" and len(tu_codes) >= 2:
                            tu_r = f"({tu_codes[0]} - {tu_codes[1]})"
                            tu_num = f"({_fmt(dong_nguon_dict.get(tu_codes[0]))} - {_fmt(dong_nguon_dict.get(tu_codes[1]))})"
                        else:
                            tu_r = "(" + " + ".join(tu_codes) + ")" if len(tu_codes) > 1 else (tu_codes[0] if tu_codes else "0")
                            tu_num_parts = [_fmt(dong_nguon_dict.get(c)) for c in tu_codes]
                            tu_num = "(" + " + ".join(tu_num_parts) + ")" if len(tu_num_parts) > 1 else (tu_num_parts[0] if tu_num_parts else "0")

                        mau_r = "(" + " + ".join(mau_codes) + ")" if len(mau_codes) > 1 else (mau_codes[0] if mau_codes else "")
                        mau_num_parts = [_fmt(dong_nguon_dict.get(c)) for c in mau_codes]
                        mau_num = "(" + " + ".join(mau_num_parts) + ")" if len(mau_num_parts) > 1 else (mau_num_parts[0] if mau_num_parts else "")

                        he_so_str = f" × {he_so}" if he_so != 1 else ""
                        unit_str = selected_ct.get('don_vi_tinh', '%')

                        if mau_r:
                            f_r_str = f"{tu_r} / {mau_r}{he_so_str}"
                            f_num_str = f"{tu_num} / {mau_num}{he_so_str}"
                        else:
                            f_r_str = f"{tu_r}{he_so_str}"
                            f_num_str = f"{tu_num}{he_so_str}"

                        if f_r_str == f_num_str:
                            bieu_thuc_the_so = f"{f_r_str} = {float(calc_val):,.3f}{unit_str}"
                        else:
                            bieu_thuc_the_so = f"{f_r_str} = {f_num_str} = {float(calc_val):,.3f}{unit_str}"
                    else:
                        resolved_v = self.resolve_metric_val(du_lieu_dict, ma_ct)
                        gia_tri_dec = to_decimal(resolved_v if resolved_v is not None else 0)

                    gia_tri_dec_rounded = round_decimal(gia_tri_dec, 4)

                    cac_muc_diem = cfg.get("cac_muc_diem", [])
                    muc_diem = NguongDiemService.tim_muc_diem(
                        gia_tri=gia_tri_dec_rounded,
                        cac_muc_diem=cac_muc_diem,
                        ma_chi_tieu=ma_ct
                    )
                    diem_ban_dau_dec = to_decimal(muc_diem.get("diem", 0))
                    diem_thuong_dec = Decimal("0")
                    diem_theo_nguong_dec = diem_ban_dau_dec
                    dien_giai = NguongDiemService.tao_dien_giai(gia_tri_dec_rounded, muc_diem)
                    has_dinh_luong = True

                diem_quy_doi_dec = (diem_theo_nguong_dec * trong_so) / Decimal("100")
                diem_quy_doi_rounded = round_decimal(diem_quy_doi_dec, 4)

                if is_dinh_tuynh:
                    tong_diem_quy_doi_dinh_tinh += diem_quy_doi_rounded
                else:
                    tong_diem_quy_doi_dinh_luong += diem_quy_doi_rounded

                ket_qua_chi_tieu_list.append(KetQuaChiTieuSchema(
                    chi_tieu_id=selected_ct["_id"],
                    ma_chi_tieu_goc=goc,
                    ma_chi_tieu_duoc_chon=ma_ct,
                    ten_chi_tieu=ten_ct,
                    cong_thuc_snapshot={
                        "mo_ta_cong_thuc": mota_goc,
                        "bieu_thuc_the_so": bieu_thuc_the_so,
                        "cong_thuc": selected_ct.get("cong_thuc")
                    },
                    du_lieu_dau_vao=decimal_to_float_or_int(du_lieu_dau_vao),
                    gia_tri_tinh_toan=float(gia_tri_dec_rounded),
                    diem_thuong=None,
                    don_vi_tinh=selected_ct.get("don_vi_tinh", "%"),
                    nguong_da_ap_dung=muc_diem,
                    diem_theo_nguong=float(diem_theo_nguong_dec),
                    trong_so=float(trong_so),
                    diem_quy_doi=float(diem_quy_doi_rounded),
                    dien_giai=dien_giai,
                    trang_thai="DA_TINH"
                ))

            diem_dl_val = float(round_decimal(tong_diem_quy_doi_dinh_luong, 4)) if has_dinh_luong else None
            diem_dt_val = float(round_decimal(tong_diem_quy_doi_dinh_tinh, 4)) if has_dinh_tinh else None

            dl_dec = tong_diem_quy_doi_dinh_luong if has_dinh_luong else Decimal("0")
            dt_dec = tong_diem_quy_doi_dinh_tinh if has_dinh_tinh else Decimal("0")

            diem_nhom_dec = dl_dec * (ts_dinh_luong / Decimal("100")) + dt_dec * (ts_dinh_tinh / Decimal("100"))
            diem_nhom_rounded = round_decimal(diem_nhom_dec, 4)

            ket_qua_nhom_list.append(KetQuaNhomSchema(
                nhom_tieu_chi_id=nhom_id,
                ma_nhom=ma_nhom,
                ten_nhom=ten_nhom,
                diem_nhom=float(diem_nhom_rounded),
                diem_dinh_luong=diem_dl_val,
                diem_dinh_tinh=diem_dt_val,
                trong_so_tieu_chi=float(ts_tieu_chi),
                trong_so_nhom_dinh_luong=float(ts_dinh_luong),
                trong_so_nhom_dinh_tinh=float(ts_dinh_tinh),
                ket_qua_cac_chi_tieu=ket_qua_chi_tieu_list
            ))
        # Attach group and criteria score mapping (diem_theo_nguong & diem_quy_doi) to du_lieu_boc_tach
        group_score_map = {
            "R-100": next((n.diem_nhom for n in ket_qua_nhom_list if n.ma_nhom == "C"), None),
            "R-115": next((n.diem_nhom for n in ket_qua_nhom_list if n.ma_nhom == "A"), None),
            "R-141": next((n.diem_nhom for n in ket_qua_nhom_list if n.ma_nhom == "M"), None),
            "R-152": next((n.diem_nhom for n in ket_qua_nhom_list if n.ma_nhom == "E"), None),
            "R-170": next((n.diem_nhom for n in ket_qua_nhom_list if n.ma_nhom == "L"), None),
            "R-184": next((n.diem_nhom for n in ket_qua_nhom_list if n.ma_nhom == "S"), None),
        }

        ct_score_map = {}
        for nhom in ket_qua_nhom_list:
            for ct in nhom.ket_qua_cac_chi_tieu:
                goc = ct.ma_chi_tieu_goc
                d_nguong = ct.diem_theo_nguong
                d_quydoi = ct.diem_quy_doi
                val_tinh = ct.gia_tri_tinh_toan

                if d_nguong is not None:
                    if goc in ["1.1.a", "1.1"]:
                        ct_score_map["R-101"] = (d_nguong, d_quydoi)
                    elif goc in ["1.2.a", "1.2"]:
                        ct_score_map["R-108"] = (d_nguong, d_quydoi)
                    elif goc == "2.1":
                        ct_score_map["R-116"] = (d_nguong, d_quydoi)
                    elif goc == "2.2":
                        ct_score_map["R-121"] = (d_nguong, d_quydoi)
                    elif goc == "2.3":
                        ct_score_map["R-124"] = (d_nguong, d_quydoi)
                        ct_score_map["R-124_VAL"] = val_tinh
                    elif goc == "2.4":
                        ct_score_map["R-127"] = (d_nguong, d_quydoi)
                    elif goc == "2.6":
                        ct_score_map["R-135"] = (d_nguong, d_quydoi)
                    elif goc == "2.7":
                        ct_score_map["R-138"] = (d_nguong, d_quydoi)
                    elif goc == "3.1":
                        ct_score_map["R-142"] = (d_nguong, d_quydoi)
                    elif goc == "4.1":
                        ct_score_map["R-153"] = (d_nguong, d_quydoi)
                    elif goc == "4.2":
                        ct_score_map["R-156"] = (d_nguong, d_quydoi)
                    elif goc == "4.3":
                        ct_score_map["R-159"] = (d_nguong, d_quydoi)
                    elif goc == "4.4":
                        ct_score_map["R-167"] = (d_nguong, d_quydoi)
                    elif goc == "5.1":
                        ct_score_map["R-171"] = (d_nguong, d_quydoi)
                    elif goc == "5.2":
                        ct_score_map["R-174"] = (d_nguong, d_quydoi)
                    elif goc == "5.3":
                        ct_score_map["R-178"] = (d_nguong, d_quydoi)
                    elif goc == "5.4":
                        ct_score_map["R-181"] = (d_nguong, d_quydoi)
                    elif goc == "6.1":
                        ct_score_map["R-185"] = (d_nguong, d_quydoi)
                    elif goc == "6.2":
                        ct_score_map["R-186"] = (d_nguong, d_quydoi)

        for item in camels_json_data:
            if isinstance(item, dict):
                code = item.get("ma_dong_nguon")
                if code == "R-124" and item.get("so_lieu") is None and "R-124_VAL" in ct_score_map:
                    item["so_lieu"] = ct_score_map["R-124_VAL"]

                if code in group_score_map and group_score_map[code] is not None:
                    item["diem_theo_nguong"] = None
                    item["diem_quy_doi"] = float(group_score_map[code])
                    item["loai_diem"] = "NHOM"
                elif code in ct_score_map:
                    ng, qd = ct_score_map[code]
                    item["diem_theo_nguong"] = float(ng) if ng is not None else None
                    item["diem_quy_doi"] = float(qd) if qd is not None else None
                    item["loai_diem"] = "CHI_TIEU"
                else:
                    item["diem_theo_nguong"] = None
                    item["diem_quy_doi"] = None
                    item["loai_diem"] = None

        tong_diem_dec, xep_hang_goc = self.tong_hop_toan_bo(ket_qua_nhom_list)
        tong_diem_rounded = round_decimal(tong_diem_dec, 2)

        # Đánh giá quy định hạ xếp hạng xuống (E) theo Khoản 7 Điều 20 Thông tư 52
        danh_gia_khoan_7 = await self.kiem_tra_dieu_20_khoan_7(
            doi_tuong_id=doi_tuong_id,
            ky_du_lieu=ky_du_lieu,
            xep_hang_goc=xep_hang_goc,
            tong_diem=float(tong_diem_rounded),
            ket_qua_cac_nhom=ket_qua_nhom_list,
            du_lieu_dict=du_lieu_dict,
            raw_dong_nguon_dict=raw_dong_nguon_dict
        )
        xep_hang_cuoi_cung = danh_gia_khoan_7["xep_hang_cuoi_cung"]

        ket_qua_id = f"KQ_{doi_tuong_id}_{ky_du_lieu}_EXCEL"

        return ThucHienTinhDiemResponse(
            ket_qua_id=ket_qua_id,
            bo_tieu_chi_id=bo_tieu_chi["_id"],
            ma_bo_tieu_chi=bo_tieu_chi.get("ma_bo_tieu_chi"),
            phien_ban_bo_tieu_chi=bo_tieu_chi.get("phien_ban"),
            du_lieu_tinh_diem_id="EXCEL_UPLOAD",
            doi_tuong={
                "ma_doi_tuong": doi_tuong.get("ma_doi_tuong", doi_tuong_id),
                "ten_doi_tuong": doi_tuong.get("ten_doi_tuong", doi_tuong_id),
                "ma_loai_doi_tuong": ma_loai_doi_tuong
            },
            ky_du_lieu=ky_du_lieu,
            tong_diem=float(tong_diem_rounded),
            xep_hang=xep_hang_cuoi_cung,
            ket_qua_cac_nhom=ket_qua_nhom_list,
            du_lieu_boc_tach=camels_json_data,
            danh_gia_khoan_7_dieu_20=danh_gia_khoan_7,
            trang_thai="HOAN_THANH",
            ngay_tinh=datetime.now().isoformat(),
            nguoi_tinh="excel_upload"
        )

    async def kiem_tra_dieu_20_khoan_7(
        self,
        doi_tuong_id: str,
        ky_du_lieu: str,
        xep_hang_goc: str,
        tong_diem: float,
        ket_qua_cac_nhom: List[KetQuaNhomSchema],
        du_lieu_dict: Dict[str, Any],
        raw_dong_nguon_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Đánh giá quy định bổ sung hạ xếp hạng xuống E theo Khoản 7 Điều 20 Thông tư 52/2018/TT-NHNN:
        a) Mất/nguy cơ mất khả năng chi trả (xem điểm nhóm Thanh khoản NTC_L):
           - Điểm 3, 4, 5: Thanh khoản bình thường đến tốt
           - Điểm 1, 2: Chờ xác nhận của Ngân hàng Nhà nước
        b) Số lỗ lũy kế > 50% giá trị VĐL và các quỹ dự trữ (dựa vào ChiTieu 7.1: R-191 / R-192 * 100)
        c) Không duy trì tỷ lệ CAR quy định trong 12 tháng liên tục HOẶC CAR < 4% trong 6 tháng liên tục (dựa vào API CAR 12 tháng)
        """
        # 1. Điều kiện a: Khả năng chi trả / thanh toán
        # Đánh giá điểm theo ngưỡng của từng chỉ tiêu trong nhóm thanh khoản (NTC_L)
        nhom_l = next((n for n in ket_qua_cac_nhom if n.ma_nhom in ["L", "NTC_L"]), None)
        chi_tieu_l_list = nhom_l.ket_qua_cac_chi_tieu if nhom_l else []

        has_item_under_2 = False
        chi_tiet_diem_a = []
        danh_sach_chi_tieu_a = []
        name_map = {
            "5.1": "Tỷ lệ tài sản thanh khoản cao",
            "5.2": "Tỷ lệ nguồn vốn ngắn hạn cho vay trung dài hạn",
            "5.3": "Tỷ lệ LDR",
            "5.4": "Tỷ lệ tiền gửi KH lớn"
        }
        for ct in chi_tieu_l_list:
            ma_ct = ct.ma_chi_tieu_duoc_chon
            if "DT" in ma_ct or ma_ct.endswith("_DT"):
                continue
            d_nguong = getattr(ct, "diem_theo_nguong", None)
            if d_nguong is None:
                d_nguong = getattr(ct, "diem_quy_doi", None)
            if d_nguong is not None:
                d_val = float(d_nguong)
                clean_name = name_map.get(ma_ct, getattr(ct, "ten_chi_tieu", ma_ct))
                chi_tiet_diem_a.append(f"{clean_name}: {d_val:.0f} điểm")
                danh_sach_chi_tieu_a.append({
                    "ma_chi_tieu": ma_ct,
                    "ten_chi_tieu": clean_name,
                    "diem": int(d_val)
                })
                if d_val < 2.0:
                    has_item_under_2 = True

        if has_item_under_2:
            dieu_kien_a = {
                "trang_thai": "CHO_XAC_NHAN_SBV",
                "vi_pham": False,  # Không ảnh hưởng đến hạ bậc xuống E
                "co_chi_tieu_duoi_2": True,
                "mo_ta": "Chưa thể xác định mất khả năng thanh khoản, chờ xác định từ NHNN",
                "chi_tiet_diem": chi_tiet_diem_a,
                "danh_sach_chi_tieu": danh_sach_chi_tieu_a
            }
        else:
            dieu_kien_a = {
                "trang_thai": "BINH_THUONG",
                "vi_pham": False,
                "co_chi_tieu_duoi_2": False,
                "mo_ta": "Khả năng thanh khoản bình thường đến tốt",
                "chi_tiet_diem": chi_tiet_diem_a,
                "danh_sach_chi_tieu": danh_sach_chi_tieu_a
            }

        # 2. Điều kiện b: Số lỗ lũy kế > 50% vốn điều lệ và các quỹ dự trữ
        r191 = raw_dong_nguon_dict.get("R-191")
        if r191 is None:
            r191 = du_lieu_dict.get("R-191")

        r192 = raw_dong_nguon_dict.get("R-192")
        if r192 is None:
            r192 = du_lieu_dict.get("R-192")

        ty_le = None
        vi_pham_b = False
        mo_ta_b = ""
        bieu_thuc_day_du = ""

        if r191 is not None and r192 is not None:
            try:
                v191 = float(r191)
                v192 = float(r192)
                if v192 != 0:
                    if v191 >= 0:
                        # R-191 >= 0: Lợi nhuận chưa phân phối dương => Lỗ lũy kế = 0
                        lo_luy_ke = 0.0
                        ty_le = 0.0
                        bieu_thuc_day_du = f"Lỗ lũy kế / VĐL & Quỹ = (0 / {v192:,.0f}) × 100% = 0%"
                        vi_pham_b = False
                        mo_ta_b = "Tỷ lệ 0% ≤ 50% VĐL & Quỹ => An toàn."
                    else:
                        # R-191 < 0: Âm => Lỗ lũy kế = |R-191|
                        lo_luy_ke = abs(v191)
                        ty_le = round((lo_luy_ke / v192) * 100, 2)
                        bieu_thuc_day_du = f"Lỗ lũy kế / VĐL & Quỹ = ({lo_luy_ke:,.0f} / {v192:,.0f}) × 100% = {ty_le}%"
                        if ty_le > 50.0:
                            vi_pham_b = True
                            mo_ta_b = f"Tỷ lệ {ty_le}% > 50% VĐL & Quỹ => Vi phạm."
                        else:
                            vi_pham_b = False
                            mo_ta_b = f"Tỷ lệ {ty_le}% ≤ 50% VĐL & Quỹ => An toàn."
            except Exception:
                pass

        if not mo_ta_b:
            mo_ta_b = "Chưa đủ dữ liệu R-191 và R-192 để tính toán."

        dieu_kien_b = {
            "vi_pham": vi_pham_b,
            "ty_le": ty_le,
            "bieu_thuc_day_du": bieu_thuc_day_du,
            "r191": r191,
            "r192": r192,
            "mo_ta": mo_ta_b
        }

        # 3. Điều kiện c: Tỷ lệ an toàn vốn (CAR) 12 tháng liên tục
        car_12_res = await self.du_lieu_tinh_diem_service.get_car_12_thang(doi_tuong_id=doi_tuong_id, thoi_gian_t=ky_du_lieu)
        car_list = car_12_res.get("du_lieu_car", [])
        valid_cars = [item.get("car") for item in car_list if item.get("car") is not None]

        vi_pham_c1_12_thang = False
        vi_pham_c2_6_thang = False

        if len(valid_cars) >= 12 and all(c < 8.0 for c in valid_cars):
            vi_pham_c1_12_thang = True

        if len(valid_cars) >= 6:
            consecutive_under_4 = 0
            max_consecutive_under_4 = 0
            for c in valid_cars:
                if c < 4.0:
                    consecutive_under_4 += 1
                    if consecutive_under_4 > max_consecutive_under_4:
                        max_consecutive_under_4 = consecutive_under_4
                else:
                    consecutive_under_4 = 0
            if max_consecutive_under_4 >= 6:
                vi_pham_c2_6_thang = True

        vi_pham_c = vi_pham_c1_12_thang or vi_pham_c2_6_thang
        reasons_c = []
        if vi_pham_c1_12_thang:
            reasons_c.append("Tỷ lệ CAR không duy trì đạt quy định trong 12 tháng liên tục")
        if vi_pham_c2_6_thang:
            reasons_c.append("Tỷ lệ CAR thấp hơn 4% trong 06 tháng liên tục")

        dieu_kien_c = {
            "vi_pham": vi_pham_c,
            "so_luong_thang_car": len(valid_cars),
            "car_thap_nhat": car_12_res.get("car_thap_nhat"),
            "mo_ta": ", ".join(reasons_c) if vi_pham_c else "Duy trì tỷ lệ an toàn vốn (CAR) đạt quy định"
        }

        # 4. Quyết định xếp hạng cuối cùng (Điều kiện a không ảnh hưởng đến việc hạ xuống E)
        ly_do_list = []
        if dieu_kien_b["vi_pham"]:
            ly_do_list.append(f"Khoản 7b: {dieu_kien_b['mo_ta']}")
        if dieu_kien_c["vi_pham"]:
            ly_do_list.append(f"Khoản 7c: {dieu_kien_c['mo_ta']}")

        bat_buoc_e = len(ly_do_list) > 0
        xep_hang_cuoi_cung = "E" if bat_buoc_e else xep_hang_goc

        if bat_buoc_e:
            ket_luan = f"Tổ chức tín dụng đạt điểm CAMELS = {tong_diem:.2f} (Xếp hạng gốc {xep_hang_goc}), tuy nhiên vi phạm quy định tại Khoản 7 Điều 20 Thông tư 52 ({'; '.join(ly_do_list)}) nên BẮT BUỘC HẠ XẾP HẠNG XUỐNG HẠNG (E)."
        else:
            ket_luan = f"Tổ chức tín dụng đạt điểm CAMELS = {tong_diem:.2f} và không vi phạm các trường hợp hạ bậc theo quy định tại Khoản 7 Điều 20 Thông tư 52, GIỮ NGUYÊN XẾP HẠNG {xep_hang_goc}."

        return {
            "dieu_kien_a_thanh_khoan": dieu_kien_a,
            "dieu_kien_b_lo_luy_ke": dieu_kien_b,
            "dieu_kien_c_vi_pham_car": dieu_kien_c,
            "bat_buoc_xep_hang_e": bat_buoc_e,
            "ly_do_xep_hang_e": ly_do_list,
            "xep_hang_goc": xep_hang_goc,
            "xep_hang_cuoi_cung": xep_hang_cuoi_cung,
            "ket_luan": ket_luan
        }

    @staticmethod
    def tong_hop_toan_bo(ket_qua_cac_nhom: List[KetQuaNhomSchema]) -> tuple[Decimal, str]:
        """
        Hàm riêng tính tổng điểm cuối cùng (tổng điểm các nhóm) và xếp hạng theo quy định nghiệp vụ (Điều 20 - Thang 5).
        """
        tong_diem_dec = Decimal("0")
        for nhom in ket_qua_cac_nhom:
            tong_diem_dec += to_decimal(nhom.diem_nhom)

        # Xếp hạng nghiệp vụ theo Điều 20 (Thang điểm 5)
        if tong_diem_dec >= Decimal("4.5"):
            xep_hang = "A"
        elif tong_diem_dec >= Decimal("3.5"):
            xep_hang = "B"
        elif tong_diem_dec >= Decimal("2.5"):
            xep_hang = "C"
        elif tong_diem_dec >= Decimal("1.5"):
            xep_hang = "D"
        else:
            xep_hang = "E"

        return tong_diem_dec, xep_hang

    async def tinh_diem_dinh_tinh_nhom(
        self,
        doi_tuong_id: str,
        ky_du_lieu: str,
        ma_nhom: str,
        du_lieu_input: Dict[str, Any],
        du_lieu_dict: Dict[str, Any]
    ) -> tuple[Decimal, str, Dict[str, Any]]:
        """
        Tính điểm định tính cho nhóm chỉ tiêu theo Khoản 3 Điều 16a Thông tư 52 (sửa đổi bổ sung bởi TT23).
        Truy vấn danh sách sai phạm từ collection 'DuLieuSaiPham' trong cơ sở dữ liệu MongoDB.
        """
        ma_nhom_clean = ma_nhom.replace("NTC_", "").upper()

        # 1. Truy vấn sai phạm từ collection mới 'DuLieuSaiPham' trong DB
        db_sai_pham = await self.du_lieu_sai_pham_repo.get_by_doi_tuong_ky_and_nhom(
            doi_tuong_id=doi_tuong_id,
            ky_du_lieu=ky_du_lieu,
            ma_nhom_chi_tieu=ma_nhom_clean
        )

        # 2. Nếu không tìm thấy trong collection 'DuLieuSaiPham', fallback sang du_lieu_input
        if not db_sai_pham:
            danh_sach_sai_pham = (
                du_lieu_input.get("danh_sach_sai_pham") or
                du_lieu_input.get("du_lieu", {}).get("danh_sach_sai_pham") or
                du_lieu_dict.get("danh_sach_sai_pham") or []
            )
        else:
            danh_sach_sai_pham = db_sai_pham

        vi_pham_nhom = []
        for item in danh_sach_sai_pham:
            item_nhom = str(item.get("ma_nhom_chi_tieu", "")).replace("NTC_", "").upper()
            if item_nhom == ma_nhom_clean or item_nhom.startswith(ma_nhom_clean):
                phat_hien_nam_xh = item.get("phat_hien_trong_nam_xep_hang", True)
                phat_hien_truoc = item.get("phat_hien_4_nam_truoc", False)
                da_khac_phuc = item.get("da_khac_phuc_song", False)
                cqql_phat_hien = item.get("co_quan_quan_ly_phat_hien", True)
                tctd_tu_baocao = item.get("tctd_tu_phat_hien", False)

                hop_le_nguon = cqql_phat_hien or tctd_tu_baocao
                hop_le_thoi_gian = phat_hien_nam_xh or (phat_hien_truoc and not da_khac_phuc)

                if hop_le_nguon and hop_le_thoi_gian:
                    vi_pham_nhom.append(item)

        if not vi_pham_nhom:
            dt_key = f"{ma_nhom_clean}_DT"
            if dt_key in du_lieu_dict and du_lieu_dict[dt_key] is not None:
                diem_dec = to_decimal(du_lieu_dict[dt_key])
                return (
                    diem_dec,
                    f"Không phát hiện sai phạm thuộc nhóm {ma_nhom_clean}. Điểm định tính do người dùng chấm/nhập trực tiếp: {float(diem_dec)} điểm",
                    {"so_luong_sai_pham": 0, "diem_co_ban": float(diem_dec), "diem_tru": 0.0}
                )
            return (
                Decimal("5.0"),
                f"Không có sai phạm thuộc nhóm {ma_nhom_clean} -> Đạt điểm định tính tối đa: 5.0 điểm",
                {"so_luong_sai_pham": 0, "diem_co_ban": 5.0, "diem_tru": 0.0}
            )

        diem_vi_pham_list = []
        tong_so_lan_vi_pham = 0
        so_lan_lap_lai_tong = 0

        for vp in vi_pham_nhom:
            so_lan = int(vp.get("so_lan_vi_pham", 1))
            tong_so_lan_vi_pham += max(so_lan, 1)
            # Số lần vi phạm lặp lại từ lần thứ 2 trở lên của riêng loại vi phạm này
            so_lan_lap_lai_tong += max(so_lan - 1, 0)

            co_phat_tien = vp.get("co_muc_phat_tien", False)
            muc_phat = vp.get("muc_phat_tien_trung_binh")
            if muc_phat is None:
                muc_phat = vp.get("muc_phat_tien_quyet_dinh")

            if co_phat_tien or (muc_phat is not None and float(muc_phat) > 0):
                m = float(muc_phat)
                if m <= 100:
                    diem_vp = Decimal("4.0")
                elif m <= 200:
                    diem_vp = Decimal("3.0")
                elif m <= 300:
                    diem_vp = Decimal("2.0")
                else:
                    diem_vp = Decimal("1.0")
            else:
                diem_vp = Decimal("4.0")

            diem_vi_pham_list.append(diem_vp)

        # Mức điểm cơ bản nhóm = MIN(các mức điểm vi phạm) (Điểm a.iii)
        diem_co_ban_dec = min(diem_vi_pham_list)

        # Trừ điểm (Điểm a.iv): Trừ 0.1 cho mỗi lần vi phạm từ lần thứ 2 trở lên đối với từng quy định, tối đa 0.9 điểm
        diem_tru_dec = min(Decimal(str(so_lan_lap_lai_tong)) * Decimal("0.1"), Decimal("0.9"))

        # Điểm định tính nhóm cuối cùng (tối thiểu 1.0)
        diem_dinh_tinh_dec = max(diem_co_ban_dec - diem_tru_dec, Decimal("1.0"))

        dien_giai = (
            f"Nhóm {ma_nhom_clean} phát hiện {len(vi_pham_nhom)} sai phạm (tổng {tong_so_lan_vi_pham} lần vi phạm, {so_lan_lap_lai_tong} lần lặp lại). "
            f"Mức điểm thấp nhất từ sai phạm: {float(diem_co_ban_dec)} điểm. "
            f"Trừ điểm ({so_lan_lap_lai_tong} lần vi phạm lặp lại từ lần thứ 2 x 0.1 điểm, tối đa 0.9 điểm): -{float(diem_tru_dec)} điểm. "
            f"-> Điểm định tính nhóm cuối cùng: {float(diem_dinh_tinh_dec)} điểm"
        )

        details = {
            "so_luong_sai_pham": len(vi_pham_nhom),
            "tong_so_lan_vi_pham": tong_so_lan_vi_pham,
            "so_lan_lap_lai_tong": so_lan_lap_lai_tong,
            "diem_co_ban": float(diem_co_ban_dec),
            "diem_tru": float(diem_tru_dec),
            "danh_sach_sai_pham_nhom": vi_pham_nhom
        }

        return diem_dinh_tinh_dec, dien_giai, details

    @staticmethod
    def resolve_metric_val(du_lieu_dict: dict, ma_ct: str, ma_bien: str = "") -> Optional[float]:
        if not isinstance(du_lieu_dict, dict):
            return None
            
        def safe_num(val):
            if val is None: return None
            try: return float(val)
            except: return None

        if ma_bien and ma_bien in du_lieu_dict and du_lieu_dict[ma_bien] is not None:
            return safe_num(du_lieu_dict[ma_bien])

        code = ma_ct or ma_bien

        # 1.1 / 1.1.a: CAR
        if code in ('1.1', '1.1.a', 'CAR', 'TY_LE_AN_TOAN_VON'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ an toàn vốn tối thiểu (CAR) (riêng lẻ)')) or safe_num(du_lieu_dict.get('Tỷ lệ an toàn vốn (CAR) hợp nhất')) or safe_num(du_lieu_dict.get('CAR'))
            if val is not None: return val
            v1 = safe_num(du_lieu_dict.get('Giá trị vốn cấp 1')) or safe_num(du_lieu_dict.get('VON_CAP_1'))
            v2 = safe_num(du_lieu_dict.get('Giá trị vốn cấp 2')) or 0.0
            rwa = safe_num(du_lieu_dict.get('Tài sản có rủi ro (RWA)')) or safe_num(du_lieu_dict.get('RWA'))
            if v1 is not None and rwa and rwa > 0:
                return round((v1 + v2) / rwa * 100, 4)
            return 0.0

        # 1.2 / 1.2.a: CAR 1
        if code in ('1.2', '1.2.a', 'CAR1', 'VON_CAP_1'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ an toàn vốn cấp 1')) or safe_num(du_lieu_dict.get('CAR1'))
            if val is not None: return val
            v1 = safe_num(du_lieu_dict.get('Giá trị vốn cấp 1')) or safe_num(du_lieu_dict.get('VON_CAP_1'))
            rwa = safe_num(du_lieu_dict.get('Tài sản có rủi ro (RWA)')) or safe_num(du_lieu_dict.get('RWA'))
            if v1 is not None and rwa and rwa > 0:
                return round(v1 / rwa * 100, 4)
            return 0.0

        # 2.1: NPL
        if code in ('2.1', 'NO_XAU', 'NO_XAU_PCT'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ nợ xấu')) or safe_num(du_lieu_dict.get('NO_XAU_PCT'))
            if val is not None: return val
            nx = safe_num(du_lieu_dict.get('Tổng nợ xấu')) or safe_num(du_lieu_dict.get('NO_XAU'))
            tdn = safe_num(du_lieu_dict.get('Tổng dư nợ cho vay khách hàng (gộp)')) or safe_num(du_lieu_dict.get('TONG_NO'))
            if nx is not None and tdn and tdn > 0:
                return round(nx / tdn * 100, 4)
            return 0.0

        # 2.2: Group 2 loan
        if code in ('2.2', 'NO_NHOM_2'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ nợ Nhóm 2 so với tổng nợ')) or safe_num(du_lieu_dict.get('NO_NHOM_2_PCT'))
            if val is not None: return val
            n2 = safe_num(du_lieu_dict.get('Nợ nhóm 2')) or safe_num(du_lieu_dict.get('NO_NHOM_2'))
            tdn = safe_num(du_lieu_dict.get('Tổng dư nợ cho vay khách hàng (gộp)')) or safe_num(du_lieu_dict.get('TONG_NO'))
            if n2 is not None and tdn and tdn > 0:
                return round(n2 / tdn * 100, 4)
            return 0.0

        # 2.3: Large borrowers
        if code in ('2.3', 'DU_NO_KHACH_HANG_LON'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ dư nợ nhóm khách hàng lớn nhất / dư nợ cho vay'))
            if val is not None: return val
            dn_lon = safe_num(du_lieu_dict.get('Dư nợ 100 khách hàng lớn nhất và người liên quan (nội bảng)')) or safe_num(du_lieu_dict.get('DU_NO_KHACH_HANG_LON'))
            tdn = safe_num(du_lieu_dict.get('Tổng dư nợ cho vay khách hàng (gộp)')) or safe_num(du_lieu_dict.get('TONG_NO'))
            if dn_lon is not None and tdn and tdn > 0:
                return round(dn_lon / tdn * 100, 4)
            return 0.0

        # 2.4: Off-balance 3-5
        if code in ('2.4', 'NO_NGOAI_BANG_3_5'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ nợ và cam kết ngoại bảng nhóm 3-5 / tổng (1-5)'))
            if val is not None: return val
            return 0.0

        # 2.5: QTDND / Agriculture
        if code == '2.5':
            val = safe_num(du_lieu_dict.get('Dư nợ ngành nông nghiệp, lâm nghiệp, thủy sản (lĩnh vực ưu tiên)'))
            tdn = safe_num(du_lieu_dict.get('Tổng dư nợ cho vay khách hàng (gộp)')) or safe_num(du_lieu_dict.get('TONG_NO'))
            if val is not None and tdn and tdn > 0:
                return round(val / tdn * 100, 4)
            return 0.0

        # 2.6: Provision for securities
        if code in ('2.6', 'DU_PHONG_CHUNG_KHOAN'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ dự phòng RR chứng khoán KD, đầu tư / số dư CK'))
            if val is not None: return val
            dp = safe_num(du_lieu_dict.get('Số dư dự phòng rủi ro tín dụng'))
            ck = safe_num(du_lieu_dict.get('Chứng khoán đầu tư'))
            if dp is not None and ck and ck > 0:
                return round(dp / ck * 100, 4)
            return 0.0

        # 2.7: Real estate
        if code in ('2.7', 'DU_NO_BAT_DONG_SAN'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ dư nợ đầu tư, kinh doanh bất động sản'))
            if val is not None: return val
            bds = safe_num(du_lieu_dict.get('Dư nợ cấp tín dụng lĩnh vực bất động sản')) or safe_num(du_lieu_dict.get('DU_NO_BAT_DONG_SAN'))
            tdn = safe_num(du_lieu_dict.get('Tổng dư nợ cho vay khách hàng (gộp)')) or safe_num(du_lieu_dict.get('TONG_NO'))
            if bds is not None and tdn and tdn > 0:
                return round(bds / tdn * 100, 4)
            return 0.0

        # 3.1: CIR
        if code in ('3.1', 'CHI_PHI_HOAT_DONG', 'CIR'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ chi phí / thu nhập (CIR)')) or safe_num(du_lieu_dict.get('CIR'))
            if val is not None: return val
            cphd = safe_num(du_lieu_dict.get('Chi phí hoạt động')) or safe_num(du_lieu_dict.get('CHI_PHI_HOAT_DONG'))
            toi = safe_num(du_lieu_dict.get('Tổng thu nhập hoạt động (TOI)')) or safe_num(du_lieu_dict.get('TONG_THU_NHAP_HOAT_DONG'))
            if cphd is not None and toi and toi > 0:
                return round(cphd / toi * 100, 4)
            return 0.0

        # 4.1: ROE
        if code in ('4.1', 'LOI_NHUAN_TRUOC_THUE', 'ROE'):
            val = safe_num(du_lieu_dict.get('Tỷ suất sinh lời vốn chủ sở hữu (ROE)')) or safe_num(du_lieu_dict.get('ROE'))
            if val is not None: return val
            lnst = safe_num(du_lieu_dict.get('Lợi nhuận sau thuế')) or safe_num(du_lieu_dict.get('Lợi nhuận trước thuế')) or safe_num(du_lieu_dict.get('LOI_NHUAN_TRUOC_THUE'))
            vcsh = safe_num(du_lieu_dict.get('Tổng vốn chủ sở hữu')) or safe_num(du_lieu_dict.get('VON_CHU_SO_HUU'))
            if lnst is not None and vcsh and vcsh > 0:
                return round(lnst / vcsh * 100, 4)
            return 0.0

        # 4.2: ROA
        if code in ('4.2', 'ROA'):
            val = safe_num(du_lieu_dict.get('Tỷ suất sinh lời tổng tài sản (ROA)')) or safe_num(du_lieu_dict.get('ROA'))
            if val is not None: return val
            lnst = safe_num(du_lieu_dict.get('Lợi nhuận sau thuế')) or safe_num(du_lieu_dict.get('Lợi nhuận trước thuế')) or safe_num(du_lieu_dict.get('LOI_NHUAN_TRUOC_THUE'))
            tts = safe_num(du_lieu_dict.get('Tổng tài sản')) or safe_num(du_lieu_dict.get('TONG_TAI_SAN'))
            if lnst is not None and tts and tts > 0:
                return round(lnst / tts * 100, 4)
            return 0.0

        # 4.3: NIM
        if code in ('4.3', 'THU_NHAP_LAI_THUAN', 'NIM'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ thu nhập lãi cận biên (NIM)')) or safe_num(du_lieu_dict.get('NIM'))
            if val is not None: return val
            nii = safe_num(du_lieu_dict.get('Thu nhập lãi thuần (NII)'))
            tts = safe_num(du_lieu_dict.get('Tổng tài sản'))
            if nii is not None and tts and tts > 0:
                return round(nii / tts * 100, 4)
            return 0.0

        # 4.4: Interest receivable days
        if code in ('4.4', 'LAI_PHAI_THU'):
            val = safe_num(du_lieu_dict.get('Số ngày lãi phải thu'))
            if val is not None: return val
            return 0.0

        # 5.1: High liquid assets
        if code in ('5.1', 'TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ tài sản thanh khoản cao bình quân / tổng tài sản bình quân'))
            if val is not None: return val
            ts_tk = safe_num(du_lieu_dict.get('Tiền mặt, chứng từ có giá trị ngoại tệ, kim loại quý')) or 0.0
            ts_tk += safe_num(du_lieu_dict.get('Tiền gửi tại Ngân hàng Nhà nước')) or 0.0
            ts_tk += safe_num(du_lieu_dict.get('Tiền gửi và cho vay các TCTD khác (tài sản)')) or 0.0
            tts = safe_num(du_lieu_dict.get('Tổng tài sản'))
            if ts_tk > 0 and tts and tts > 0:
                return round(ts_tk / tts * 100, 4)
            return 0.0

        # 5.2: Short term for medium-long term loans
        if code in ('5.2', 'VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ nguồn vốn ngắn hạn được sử dụng để cho vay trung và dài hạn'))
            if val is not None: return val
            return 0.0

        # 5.3: LDR
        if code in ('5.3', 'DU_NO_CHO_VAY', 'LDR'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ dư nợ cho vay so với tổng tiền gửi (LDR)')) or safe_num(du_lieu_dict.get('LDR'))
            if val is not None: return val
            tdn = safe_num(du_lieu_dict.get('Tổng dư nợ cho vay khách hàng (gộp)')) or safe_num(du_lieu_dict.get('DU_NO_CHO_VAY'))
            ttg = safe_num(du_lieu_dict.get('Tổng tiền gửi của khách hàng và Phát hành giấy tờ có giá')) or safe_num(du_lieu_dict.get('Tổng tiền gửi')) or safe_num(du_lieu_dict.get('TONG_TIEN_GUI'))
            if tdn is not None and ttg and ttg > 0:
                return round(tdn / ttg * 100, 4)
            return 0.0

        # 5.4: CASA / Large deposits
        if code in ('5.4', 'TIEN_GUI_KHACH_HANG_LON'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ tiền gửi không kỳ hạn (CASA)')) or safe_num(du_lieu_dict.get('CASA'))
            if val is not None: return val
            return 0.0

        # 6.1: Foreign currency position
        if code in ('6.1', 'TY_LE_TRANG_THAI_NGOAI_TE'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ trạng thái ngoại tệ trên vốn tự có'))
            if val is not None: return val
            return 0.0

        # 6.2: Interest rate sensitive asset/liability gap
        if code in ('6.2', 'TAI_SAN_NHAY_CAM_LAI_SUAT'):
            val = safe_num(du_lieu_dict.get('Tỷ lệ chênh lệch tài sản - nợ nhạy cảm lãi suất / vốn chủ sở hữu'))
            if val is not None: return val
            ts_ls = safe_num(du_lieu_dict.get('Tổng giá trị tài sản nhạy cảm với lãi suất')) or safe_num(du_lieu_dict.get('TAI_SAN_NHAY_CAM_LAI_SUAT'))
            no_ls = safe_num(du_lieu_dict.get('Nợ phải trả nhạy cảm với lãi suất')) or safe_num(du_lieu_dict.get('NO_NHAY_CAM_LAI_SUAT'))
            vcsh = safe_num(du_lieu_dict.get('Tổng vốn chủ sở hữu')) or safe_num(du_lieu_dict.get('VON_CHU_SO_HUU'))
            if ts_ls is not None and no_ls is not None and vcsh and vcsh > 0:
                return round(abs(ts_ls - no_ls) / vcsh * 100, 4)
            return 0.0

        return None
