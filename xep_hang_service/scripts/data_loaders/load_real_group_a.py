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
logger = logging.getLogger("seed_group_a")

def make_muc_diem_cang_nho_cang_tot(n1, n2, n3, n4):
    """
    Tạo 5 mức điểm cho chỉ tiêu CÀNG NHỎ CÀNG TỐT:
    (i) Điểm 5: <= Ngưỡng 1
    (ii) Điểm 4: > Ngưỡng 1 và <= Ngưỡng 2
    (iii) Điểm 3: > Ngưỡng 2 và <= Ngưỡng 3
    (iv) Điểm 2: > Ngưỡng 3 và <= Ngưỡng 4
    (v) Điểm 1: > Ngưỡng 4
    """
    return [
        {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": n1, "bao_gom_den": True},
        {"thu_tu": 2, "diem": 4, "tu": n1, "bao_gom_tu": False, "den": n2, "bao_gom_den": True},
        {"thu_tu": 3, "diem": 3, "tu": n2, "bao_gom_tu": False, "den": n3, "bao_gom_den": True},
        {"thu_tu": 4, "diem": 2, "tu": n3, "bao_gom_tu": False, "den": n4, "bao_gom_den": True},
        {"thu_tu": 5, "diem": 1, "tu": n4, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
    ]

async def run_load_group_a():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. NẠP NHÓM 2: CHẤT LƯỢNG TÀI SẢN (A)
    nhom_a = {
        "_id": "NTC_A",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "A",
        "so_thu_tu": 2,
        "ten_nhom": "CHẤT LƯỢNG TÀI SẢN (A)",
        "trong_so_tieu_chi": 30.0,
        "trong_so_nhom_dinh_luong": 25.0,
        "thu_tu_hien_thi": 2,
        "ghi_chu": "Trọng số tiêu chí: 30,00%; trọng số nhóm định lượng: 25,00%",
        "is_active": 1
    }
    await db.NhomTieuChi.replace_one({"_id": "NTC_A"}, nhom_a, upsert=True)
    logger.info("Đã nạp NhomTieuChi: NTC_A (CHẤT LƯỢNG TÀI SẢN)")

    # 2. XÓA CÁC CHỈ TIÊU CŨ CỦA NHÓM A NẾU CÓ
    await db.ChiTieu.delete_many({"nhom_tieu_chi_id": "NTC_A"})

    # -------------------------------------------------------------
    # Chỉ tiêu 2.1: Tỷ lệ nợ xấu, nợ xấu VAMC, nợ cơ cấu...
    # -------------------------------------------------------------
    ct_2_1 = {
        "_id": "CT_2_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.1",
        "ma_chi_tieu_goc": "2.1",
        "ten_chi_tieu": "Tỷ lệ nợ xấu, nợ xấu đã bán cho VAMC chưa xử lý được và nợ cơ cấu tiềm ẩn trở thành nợ xấu so với tổng nợ cộng thêm các khoản nợ xấu đã bán cho VAMC chưa xử lý được",
        "mo_ta_cong_thuc": "Tử số: Nợ xấu + Nợ xấu bán VAMC chưa xử lý + Nợ cơ cấu tiềm ẩn thành nợ xấu. Mẫu số: Tổng nợ + Nợ xấu bán VAMC chưa xử lý x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {
                            "phep_toan": "CONG",
                            "tham_so": [
                                {"ma_bien": "NO_XAU"},
                                {"ma_bien": "NO_XAU_VAMC_CHUA_XU_LY"},
                                {"ma_bien": "NO_CO_TIEM_AN_THANH_NO_XAU"}
                            ]
                        },
                        {
                            "phep_toan": "CONG",
                            "tham_so": [
                                {"ma_bien": "TONG_NO"},
                                {"ma_bien": "NO_XAU_VAMC_CHUA_XU_LY"}
                            ]
                        }
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "NO_XAU", "ten_bien": "Nợ xấu", "bat_buoc": True},
            {"ma_bien": "NO_XAU_VAMC_CHUA_XU_LY", "ten_bien": "Nợ xấu bán cho VAMC chưa xử lý được", "bat_buoc": True},
            {"ma_bien": "NO_CO_TIEM_AN_THANH_NO_XAU", "ten_bien": "Nợ cơ cấu tiềm ẩn trở thành nợ xấu", "bat_buoc": True},
            {"ma_bien": "TONG_NO", "ten_bien": "Tổng nợ", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 3.00, 5.00, 7.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 3.00, 5.00, 7.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 3.00, 5.00, 7.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 4.00, 6.00, 8.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 3.00, 5.00, 7.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 3.00, 5.00, 7.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 sửa đổi ngưỡng và trọng số.",
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 2.2: Tỷ lệ nợ Nhóm 2 so với tổng nợ
    # -------------------------------------------------------------
    ct_2_2 = {
        "_id": "CT_2_2",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.2",
        "ma_chi_tieu_goc": "2.2",
        "ten_chi_tieu": "Tỷ lệ nợ Nhóm 2 so với tổng nợ",
        "mo_ta_cong_thuc": "Nợ nhóm 2 / Tổng nợ x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "NO_NHOM_2"},
                        {"ma_bien": "TONG_NO"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "NO_NHOM_2", "ten_bien": "Nợ nhóm 2", "bat_buoc": True},
            {"ma_bien": "TONG_NO", "ten_bien": "Tổng nợ", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 15.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.50, 4.00, 5.50, 7.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 15.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.50, 4.00, 5.50, 7.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 25.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.50, 4.00, 5.50, 7.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.50, 5.00, 6.00, 8.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.50, 4.00, 5.50, 7.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.50, 4.00, 5.50, 7.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 sửa đổi ngưỡng.",
        "thu_tu_hien_thi": 2,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 2.3: Tỷ lệ dư nợ tín dụng các khách hàng lớn
    # -------------------------------------------------------------
    ct_2_3 = {
        "_id": "CT_2_3",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.3",
        "ma_chi_tieu_goc": "2.3",
        "ten_chi_tieu": "Tỷ lệ dư nợ tín dụng của các khách hàng có dư nợ tín dụng lớn so với dư nợ tín dụng đối với tổ chức kinh tế, cá nhân",
        "mo_ta_cong_thuc": "Dư nợ cấp tín dụng/tín dụng của các khách hàng có dư nợ cấp tín dụng/tín dụng lớn / Dư nợ cấp tín dụng/tín dụng đối với tổ chức kinh tế, cá nhân x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "DU_NO_KHACH_HANG_LON"},
                        {"ma_bien": "DU_NO_TO_CHUC_CA_NHAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "DU_NO_KHACH_HANG_LON", "ten_bien": "Dư nợ các khách hàng có dư nợ lớn", "bat_buoc": True},
            {"ma_bien": "DU_NO_TO_CHUC_CA_NHAN", "ten_bien": "Dư nợ đối với tổ chức kinh tế, cá nhân", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 25.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 15.00, 20.00, 25.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 25.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 20.00, 30.00, 40.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 20.00, 30.00, 40.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 10.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 10.00, 15.00, 20.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 sửa tên chỉ tiêu và trọng số; ngưỡng giữ theo TT52.",
        "thu_tu_hien_thi": 3,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 2.4: Tỷ lệ nợ và cam kết ngoại bảng từ nhóm 3 đến nhóm 5
    # -------------------------------------------------------------
    ct_2_4 = {
        "_id": "CT_2_4",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.4",
        "ma_chi_tieu_goc": "2.4",
        "ten_chi_tieu": "Tỷ lệ nợ và cam kết ngoại bảng từ nhóm 3 đến nhóm 5 so với tổng nợ và các cam kết ngoại bảng từ nhóm 1 đến nhóm 5",
        "mo_ta_cong_thuc": "Nợ và cam kết ngoại bảng từ nhóm 3 đến nhóm 5 / Tổng nợ và cam kết ngoại bảng từ nhóm 1 đến nhóm 5 x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "NO_NGOAI_BANG_3_5"},
                        {"ma_bien": "TONG_NO_NGOAI_BANG_1_5"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "NO_NGOAI_BANG_3_5", "ten_bien": "Nợ và cam kết ngoại bảng nhóm 3-5", "bat_buoc": True},
            {"ma_bien": "TONG_NO_NGOAI_BANG_1_5", "ten_bien": "Tổng nợ và cam kết ngoại bảng nhóm 1-5", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(1.00, 2.00, 3.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(1.50, 2.50, 3.50, 7.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(1.00, 2.50, 3.50, 7.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 15.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(1.00, 3.00, 5.00, 8.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 10.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(1.00, 2.50, 4.00, 7.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 15.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(1.00, 2.50, 3.50, 7.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 sửa trọng số; ngưỡng giữ theo TT52.",
        "thu_tu_hien_thi": 4,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 2.5: Tỷ lệ dư nợ cho vay thành viên QTDND
    # -------------------------------------------------------------
    ct_2_5 = {
        "_id": "CT_2_5",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.5",
        "ma_chi_tieu_goc": "2.5",
        "ten_chi_tieu": "Tỷ lệ dư nợ cho vay thành viên quỹ tín dụng nhân dân so với tổng dư nợ cho vay",
        "mo_ta_cong_thuc": "Dư nợ cho vay thành viên QTDND / Tổng dư nợ cho vay x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "DU_NO_THANH_VIEN_QTDND"},
                        {"ma_bien": "TONG_DU_NO_CHO_VAY"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "DU_NO_THANH_VIEN_QTDND", "ten_bien": "Dư nợ cho vay thành viên QTDND", "bat_buoc": True},
            {"ma_bien": "TONG_DU_NO_CHO_VAY", "ten_bien": "Tổng dư nợ cho vay", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 10.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 20.00, 30.00, 40.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 sửa trọng số; ngưỡng giữ theo TT52.",
        "thu_tu_hien_thi": 5,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 2.6: Tỷ lệ dự phòng rủi ro chứng khoán
    # -------------------------------------------------------------
    ct_2_6 = {
        "_id": "CT_2_6",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.6",
        "ma_chi_tieu_goc": "2.6",
        "ten_chi_tieu": "Tỷ lệ dự phòng rủi ro chứng khoán kinh doanh, chứng khoán đầu tư (không bao gồm dự phòng rủi ro đã trích lập liên quan đến trái phiếu đặc biệt khi bán nợ cho VAMC) so với tổng số dư chứng khoán kinh doanh, chứng khoán đầu tư",
        "mo_ta_cong_thuc": "Dự phòng rủi ro chứng khoán kinh doanh, chứng khoán đầu tư / Tổng số dư chứng khoán kinh doanh, chứng khoán đầu tư x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "DU_PHONG_CHUNG_KHOAN"},
                        {"ma_bien": "TONG_SO_DU_CHUNG_KHOAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "DU_PHONG_CHUNG_KHOAN", "ten_bien": "Dự phòng rủi ro chứng khoán kinh doanh, đầu tư", "bat_buoc": True},
            {"ma_bien": "TONG_SO_DU_CHUNG_KHOAN", "ten_bien": "Tổng số dư chứng khoán kinh doanh, đầu tư", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(3.00, 5.00, 10.00, 15.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 7.00, 12.00, 17.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 7.00, 12.00, 17.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 7.00, 12.00, 17.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(2.00, 5.00, 7.00, 10.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 6,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 2.7: Tỷ lệ dư nợ tín dụng để đầu tư, kinh doanh bất động sản
    # -------------------------------------------------------------
    ct_2_7 = {
        "_id": "CT_2_7",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.7",
        "ma_chi_tieu_goc": "2.7",
        "ten_chi_tieu": "Tỷ lệ dư nợ tín dụng để đầu tư, kinh doanh bất động sản so với tổng dư nợ tín dụng",
        "mo_ta_cong_thuc": "Dư nợ tín dụng để đầu tư, kinh doanh bất động sản / Tổng dư nợ tín dụng x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "DU_NO_BAT_DONG_SAN"},
                        {"ma_bien": "TONG_DU_NO_TIN_DUNG"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "DU_NO_BAT_DONG_SAN", "ten_bien": "Dư nợ tín dụng đầu tư kinh doanh bất động sản", "bat_buoc": True},
            {"ma_bien": "TONG_DU_NO_TIN_DUNG", "ten_bien": "Tổng dư nợ tín dụng", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 10.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 10.00, 15.00, 20.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 10.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 10.00, 15.00, 20.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 5.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(4.00, 8.00, 12.00, 16.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23. TT23 sửa thành chỉ tiêu tỷ lệ dư nợ tín dụng để đầu tư, kinh doanh bất động sản và sửa ngưỡng/trọng số.",
        "thu_tu_hien_thi": 7,
        "is_active": 1
    }

    await db.ChiTieu.insert_many([ct_2_1, ct_2_2, ct_2_3, ct_2_4, ct_2_5, ct_2_6, ct_2_7])
    logger.info("Đã nạp 7 chỉ tiêu chính thức nhóm CHẤT LƯỢNG TÀI SẢN (A): 2.1 - 2.7!")

    # 3. CẬP NHẬT DỮ LIỆU TÍNH ĐIỂM KỲ 2025 CỦA NH_001 ĐỂ CÓ THÊM BIẾN CHO NHÓM A
    await db.DuLieuTinhDiem.update_one(
        {"_id": "DL_NH001_2025_V1"},
        {"$set": {
            "du_lieu.NO_XAU": 900,
            "du_lieu.NO_XAU_VAMC_CHUA_XU_LY": 100,
            "du_lieu.NO_CO_TIEM_AN_THANH_NO_XAU": 120,
            "du_lieu.TONG_NO": 40000,
            "du_lieu.NO_NHOM_2": 1280,
            "du_lieu.DU_NO_KHACH_HANG_LON": 10000,
            "du_lieu.DU_NO_TO_CHUC_CA_NHAN": 50000,
            "du_lieu.NO_NGOAI_BANG_3_5": 200,
            "du_lieu.TONG_NO_NGOAI_BANG_1_5": 42000,
            "du_lieu.DU_PHONG_CHUNG_KHOAN": 150,
            "du_lieu.TONG_SO_DU_CHUNG_KHOAN": 10000,
            "du_lieu.DU_NO_BAT_DONG_SAN": 3500,
            "du_lieu.TONG_DU_NO_TIN_DUNG": 40000
        }}
    )
    logger.info("Đã cập nhật dữ liệu đầu vào kỳ 2025 cho NH_001!")

    logger.info("🎉 ĐÃ NẠP THÀNH CÔNG DỮ LIỆU THẬT CHO NHÓM CHẤT LƯỢNG TÀI SẢN (A)!")

if __name__ == "__main__":
    asyncio.run(run_load_group_a())
