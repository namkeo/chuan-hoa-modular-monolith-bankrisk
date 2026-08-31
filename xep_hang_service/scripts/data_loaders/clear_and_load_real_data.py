import asyncio
import logging
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_real_data")

def make_muc_diem_cang_lon_cang_tot(n1, n2, n3, n4):
    """
    Tạo 5 mức điểm cho chỉ tiêu CÀNG LỚN CÀNG TỐT:
    (i) Điểm 5: >= Ngưỡng 1
    (ii) Điểm 4: >= Ngưỡng 2 và < Ngưỡng 1
    (iii) Điểm 3: >= Ngưỡng 3 và < Ngưỡng 2
    (iv) Điểm 2: >= Ngưỡng 4 và < Ngưỡng 3
    (v) Điểm 1: < Ngưỡng 4
    """
    return [
        {"thu_tu": 1, "diem": 5, "tu": n1, "bao_gom_tu": True, "den": None, "bao_gom_den": False},
        {"thu_tu": 2, "diem": 4, "tu": n2, "bao_gom_tu": True, "den": n1, "bao_gom_den": False},
        {"thu_tu": 3, "diem": 3, "tu": n3, "bao_gom_tu": True, "den": n2, "bao_gom_den": False},
        {"thu_tu": 4, "diem": 2, "tu": n4, "bao_gom_tu": True, "den": n3, "bao_gom_den": False},
        {"thu_tu": 5, "diem": 1, "tu": None, "bao_gom_tu": False, "den": n4, "bao_gom_den": False}
    ]

async def run_clear_and_load():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. XÓA SẠCH TẤT CẢ DỮ LIỆU TẠM HIỆN TẠI
    logger.info("Xóa dữ liệu cũ tại tất cả các collection...")
    await db.BoTieuChi.delete_many({})
    await db.NhomTieuChi.delete_many({})
    await db.ChiTieu.delete_many({})
    await db.DoiTuongDanhGia.delete_many({})
    await db.DuLieuTinhDiem.delete_many({})
    await db.KetQuaTinhDiem.delete_many({})
    logger.info("Đã xóa sạch dữ liệu cũ!")

    # 2. NẠP BỘ TIÊU CHÍ CHÍNH THỨC 2026
    bo_tieu_chi_data = {
        "_id": "BTC_2026_V1",
        "ma_bo_tieu_chi": "BTC_2026",
        "ten_bo_tieu_chi": "Bộ tiêu chí đánh giá rủi ro tổ chức tín dụng",
        "phien_ban": 1,
        "tu_ngay": "2026-01-01",
        "den_ngay": None,
        "trang_thai": "DANG_AP_DUNG",
        "mo_ta": "Bộ tiêu chí chính thức theo Thông tư 52 và Thông tư 23 sửa đổi bổ sung",
        "can_cu_phap_ly": [
            {"ma_van_ban": "TT52", "ten_van_ban": "Thông tư số 52/2018/TT-NHNN"},
            {"ma_van_ban": "TT23", "ten_van_ban": "Thông tư số 23/2020/TT-NHNN sửa đổi, bổ sung Thông tư 52"}
        ],
        "ngay_tao": "2026-07-27T10:00:00",
        "nguoi_tao": "admin",
        "is_active": 1
    }
    await db.BoTieuChi.insert_one(bo_tieu_chi_data)
    logger.info("Đã tạo BoTieuChi: BTC_2026_V1")

    # 3. NẠP NHÓM 1: VỐN (C)
    nhom_c = {
        "_id": "NTC_C",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "C",
        "so_thu_tu": 1,
        "ten_nhom": "VỐN (C)",
        "trong_so_tieu_chi": 20.0,
        "trong_so_nhom_dinh_luong": 15.0,
        "thu_tu_hien_thi": 1,
        "ghi_chu": "Trọng số tiêu chí: 20,00%; trọng số nhóm định lượng: 15,00%",
        "is_active": 1
    }
    await db.NhomTieuChi.insert_one(nhom_c)
    logger.info("Đã tạo NhomTieuChi: NTC_C (VỐN)")

    # 4. NẠP DỮ LIỆU CÁC CHỈ TIÊU NHÓM VỐN (C)

    # -------------------------------------------------------------
    # Chỉ tiêu 1.1: CAR không theo TT41
    # -------------------------------------------------------------
    ct_1_1 = {
        "_id": "CT_1_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "1.1",
        "ma_chi_tieu_goc": "1.1",
        "ten_chi_tieu": "Tỷ lệ an toàn vốn (không bao gồm trường hợp thực hiện theo quy định tại Thông tư số 41/2016/TT-NHNN)",
        "mo_ta_cong_thuc": "Tỷ lệ an toàn vốn = Vốn tự có / Tổng tài sản Có rủi ro x 100% (theo quy định về giới hạn, tỷ lệ bảo đảm an toàn).",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "VON_TU_CO"},
                        {"ma_bien": "TONG_TAI_SAN_CO_RUI_RO"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "VON_TU_CO", "ten_bien": "Vốn tự có", "bat_buoc": True},
            {"ma_bien": "TONG_TAI_SAN_CO_RUI_RO", "ten_bien": "Tổng tài sản Có rủi ro", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {
            "kieu": "SO_SANH",
            "truong": "ap_dung_thong_tu_41",
            "phep_so_sanh": "BANG",
            "gia_tri": False
        },
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(15.00, 12.00, 8.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(15.00, 12.00, 8.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(15.00, 12.00, 8.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(20.00, 16.00, 9.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(20.00, 16.00, 9.00, 6.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(15.00, 12.00, 9.00, 5.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 tách ngưỡng theo trường hợp không thực hiện Thông tư 41/2016/TT-NHNN.",
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 1.1.a: CAR thực hiện theo TT41
    # -------------------------------------------------------------
    ct_1_1_a = {
        "_id": "CT_1_1_A",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "1.1.a",
        "ma_chi_tieu_goc": "1.1",
        "ten_chi_tieu": "Tỷ lệ an toàn vốn (thực hiện theo quy định tại Thông tư số 41/2016/TT-NHNN)",
        "mo_ta_cong_thuc": "Tỷ lệ an toàn vốn theo Thông tư 41/2016/TT-NHNN: CAR = C / [RWA + 12,5 x (KOR + KMR)] x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "C"},
                        {
                            "phep_toan": "CONG",
                            "tham_so": [
                                {"ma_bien": "RWA"},
                                {
                                    "phep_toan": "NHAN",
                                    "tham_so": [
                                        {"gia_tri": 12.5},
                                        {
                                            "phep_toan": "CONG",
                                            "tham_so": [
                                                {"ma_bien": "KOR"},
                                                {"ma_bien": "KMR"}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "C", "ten_bien": "Vốn tự có", "bat_buoc": True},
            {"ma_bien": "RWA", "ten_bien": "Tài sản Có rủi ro tín dụng", "bat_buoc": True},
            {"ma_bien": "KOR", "ten_bien": "Vốn yêu cầu rủi ro hoạt động", "bat_buoc": True},
            {"ma_bien": "KMR", "ten_bien": "Vốn yêu cầu rủi ro thị trường", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {
            "kieu": "SO_SANH",
            "truong": "ap_dung_thong_tu_41",
            "phep_so_sanh": "BANG",
            "gia_tri": True
        },
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(11.00, 9.00, 7.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(11.00, 9.00, 7.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(15.00, 12.00, 8.00, 5.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 bổ sung ngưỡng đối với trường hợp thực hiện theo Thông tư 41/2016/TT-NHNN; chỉ áp dụng thay thế cho 1.1 khi dùng đối tượng/phương pháp.",
        "thu_tu_hien_thi": 2,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 1.2: Tỷ lệ an toàn vốn cấp 1 không theo TT41
    # -------------------------------------------------------------
    ct_1_2 = {
        "_id": "CT_1_2",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "1.2",
        "ma_chi_tieu_goc": "1.2",
        "ten_chi_tieu": "Tỷ lệ an toàn vốn cấp 1 (không bao gồm trường hợp thực hiện theo quy định tại Thông tư số 41/2016/TT-NHNN)",
        "mo_ta_cong_thuc": "TT52: Tỷ lệ an toàn vốn cấp 1 = Vốn cấp 1 riêng lẻ / Tổng tài sản Có rủi ro riêng lẻ x 100%. TT23: áp dụng công thức tương ứng theo quy định về giới hạn, tỷ lệ bảo đảm an toàn.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "VON_CAP_1"},
                        {"ma_bien": "TONG_TAI_SAN_CO_RUI_RO"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "VON_CAP_1", "ten_bien": "Vốn cấp 1", "bat_buoc": True},
            {"ma_bien": "TONG_TAI_SAN_CO_RUI_RO", "ten_bien": "Tổng tài sản Có rủi ro", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {
            "kieu": "SO_SANH",
            "truong": "ap_dung_thong_tu_41",
            "phep_so_sanh": "BANG",
            "gia_tri": False
        },
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(12.00, 10.00, 7.00, 4.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(12.00, 10.00, 7.00, 4.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(12.00, 10.00, 7.00, 4.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(13.00, 10.00, 8.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(13.00, 10.00, 8.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(12.00, 10.00, 7.00, 4.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 tách ngưỡng theo trường hợp không thực hiện Thông tư 41/2016/TT-NHNN.",
        "thu_tu_hien_thi": 3,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 1.2.a: Tỷ lệ an toàn vốn cấp 1 thực hiện theo TT41
    # -------------------------------------------------------------
    ct_1_2_a = {
        "_id": "CT_1_2_A",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "1.2.a",
        "ma_chi_tieu_goc": "1.2",
        "ten_chi_tieu": "Tỷ lệ an toàn vốn cấp 1 (thực hiện theo quy định tại Thông tư số 41/2016/TT-NHNN)",
        "mo_ta_cong_thuc": "Tỷ lệ an toàn vốn cấp 1 theo Thông tư 41/2016/TT-NHNN = Vốn cấp 1 / [RWA + 12,5 x (KOR + KMR)] x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "VON_CAP_1"},
                        {
                            "phep_toan": "CONG",
                            "tham_so": [
                                {"ma_bien": "RWA"},
                                {
                                    "phep_toan": "NHAN",
                                    "tham_so": [
                                        {"gia_tri": 12.5},
                                        {
                                            "phep_toan": "CONG",
                                            "tham_so": [
                                                {"ma_bien": "KOR"},
                                                {"ma_bien": "KMR"}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "VON_CAP_1", "ten_bien": "Vốn cấp 1", "bat_buoc": True},
            {"ma_bien": "RWA", "ten_bien": "Tài sản Có rủi ro tín dụng", "bat_buoc": True},
            {"ma_bien": "KOR", "ten_bien": "Vốn yêu cầu rủi ro hoạt động", "bat_buoc": True},
            {"ma_bien": "KMR", "ten_bien": "Vốn yêu cầu rủi ro thị trường", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {
            "kieu": "SO_SANH",
            "truong": "ap_dung_thong_tu_41",
            "phep_so_sanh": "BANG",
            "gia_tri": True
        },
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(8.50, 7.00, 5.50, 4.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(8.50, 7.00, 5.50, 4.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(12.00, 10.00, 7.00, 4.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 bổ sung ngưỡng đối với trường hợp thực hiện theo Thông tư 41/2016/TT-NHNN; chỉ áp dụng thay thế cho 1.2 khi dùng đối tượng/phương pháp.",
        "thu_tu_hien_thi": 4,
        "is_active": 1
    }

    await db.ChiTieu.insert_many([ct_1_1, ct_1_1_a, ct_1_2, ct_1_2_a])
    logger.info("Đã nạp 4 chỉ tiêu chính thức nhóm VỐN (C): 1.1, 1.1.a, 1.2, 1.2.a!")

    # 5. NẠP CÁC ĐỐI TƯỢNG ĐÁNH GIÁ MẪU CHO MỖI LOẠI HÌNH
    doi_tuong_list = [
        {
            "_id": "NH_001",
            "ma_doi_tuong": "NH_001",
            "ten_doi_tuong": "Ngân hàng Thương mại Cổ phần A (Quy mô lớn)",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True, "quy_mo": "LON"},
            "is_active": 1
        },
        {
            "_id": "NH_002",
            "ma_doi_tuong": "NH_002",
            "ten_doi_tuong": "Ngân hàng Thương mại Cổ phần B (Quy mô nhỏ)",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
            "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
            "thuoc_tinh": {"ap_dung_thong_tu_41": False, "quy_mo": "NHO"},
            "is_active": 1
        },
        {
            "_id": "CTTC_001",
            "ma_doi_tuong": "CTTC_001",
            "ten_doi_tuong": "Công ty Tài chính X",
            "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
            "ten_loai_doi_tuong": "Công ty tài chính",
            "thuoc_tinh": {"ap_dung_thong_tu_41": False},
            "is_active": 1
        }
    ]
    await db.DoiTuongDanhGia.insert_many(doi_tuong_list)
    logger.info("Đã nạp danh sách Đối tượng đánh giá mẫu!")

    # 6. NẠP DỮ LIỆU TÍNH ĐIỂM CHUẨN MẪU Cho Kỳ 2025
    du_lieu_tinh_diem_list = [
        {
            "_id": "DL_NH001_2025_V1",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True},
            "du_lieu": {
                "C": 10000,
                "RWA": 90000,
                "KOR": 100,
                "KMR": 50,
                "VON_CAP_1": 8500
            },
            "trang_thai": "DA_PHE_DUYET",
            "nguoi_nhap": "user01",
            "ngay_nhap": "2026-07-27T08:00:00",
            "nguoi_phe_duyet": "user02",
            "ngay_phe_duyet": "2026-07-27T09:00:00",
            "is_active": 1
        },
        {
            "_id": "DL_NH002_2025_V1",
            "doi_tuong_id": "NH_002",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
            "thuoc_tinh": {"ap_dung_thong_tu_41": False},
            "du_lieu": {
                "VON_TU_CO": 1300,
                "TONG_TAI_SAN_CO_RUI_RO": 10000,
                "VON_CAP_1": 1100
            },
            "trang_thai": "DA_PHE_DUYET",
            "nguoi_nhap": "user01",
            "ngay_nhap": "2026-07-27T08:00:00",
            "nguoi_phe_duyet": "user02",
            "ngay_phe_duyet": "2026-07-27T09:00:00",
            "is_active": 1
        }
    ]
    await db.DuLieuTinhDiem.insert_many(du_lieu_tinh_diem_list)
    logger.info("Đã nạp Dữ liệu tính điểm mẫu kỳ 2025!")

    logger.info("🎉 ĐÃ XÓA SẠCH VÀ NẠP THÀNH CÔNG DỮ LIỆU THẬT CHO NHÓM VỐN (C)!")

if __name__ == "__main__":
    asyncio.run(run_clear_and_load())
