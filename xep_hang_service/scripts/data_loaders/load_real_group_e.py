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
logger = logging.getLogger("seed_group_e")

def make_muc_diem_cang_lon_cang_tot(n1, n2, n3, n4):
    return [
        {"thu_tu": 1, "diem": 5, "tu": n1, "bao_gom_tu": True, "den": None, "bao_gom_den": False},
        {"thu_tu": 2, "diem": 4, "tu": n2, "bao_gom_tu": True, "den": n1, "bao_gom_den": False},
        {"thu_tu": 3, "diem": 3, "tu": n3, "bao_gom_tu": True, "den": n2, "bao_gom_den": False},
        {"thu_tu": 4, "diem": 2, "tu": n4, "bao_gom_tu": True, "den": n3, "bao_gom_den": False},
        {"thu_tu": 5, "diem": 1, "tu": None, "bao_gom_tu": False, "den": n4, "bao_gom_den": False}
    ]

def make_muc_diem_cang_nho_cang_tot(n1, n2, n3, n4):
    return [
        {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": n1, "bao_gom_den": True},
        {"thu_tu": 2, "diem": 4, "tu": n1, "bao_gom_tu": False, "den": n2, "bao_gom_den": True},
        {"thu_tu": 3, "diem": 3, "tu": n2, "bao_gom_tu": False, "den": n3, "bao_gom_den": True},
        {"thu_tu": 4, "diem": 2, "tu": n3, "bao_gom_tu": False, "den": n4, "bao_gom_den": True},
        {"thu_tu": 5, "diem": 1, "tu": n4, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
    ]

async def run_load_group_e():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. NẠP NHÓM 4: KẾT QUẢ HOẠT ĐỘNG KINH DOANH (E)
    nhom_e = {
        "_id": "NTC_E",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "E",
        "so_thu_tu": 4,
        "ten_nhom": "KẾT QUẢ HOẠT ĐỘNG KINH DOANH (E)",
        "trong_so_tieu_chi": 20.0,
        "trong_so_nhom_dinh_luong": 15.0,
        "thu_tu_hien_thi": 4,
        "ghi_chu": "Trọng số tiêu chí: 20,00%; trọng số nhóm định lượng: 15,00%",
        "is_active": 1
    }
    await db.NhomTieuChi.replace_one({"_id": "NTC_E"}, nhom_e, upsert=True)
    logger.info("Đã nạp NhomTieuChi: NTC_E (KẾT QUẢ HOẠT ĐỘNG KINH DOANH)")

    # 2. XÓA CÁC CHỈ TIÊU CỦA NHÓM E NẾU CÓ
    await db.ChiTieu.delete_many({"nhom_tieu_chi_id": "NTC_E"})

    # -------------------------------------------------------------
    # Chỉ tiêu 4.1: Tỷ lệ lợi nhuận trước thuế so với vốn chủ sở hữu bình quân (ROE)
    # -------------------------------------------------------------
    ct_4_1 = {
        "_id": "CT_4_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_E",
        "ma_chi_tieu": "4.1",
        "ma_chi_tieu_goc": "4.1",
        "ten_chi_tieu": "Tỷ lệ lợi nhuận trước thuế so với vốn chủ sở hữu bình quân",
        "mo_ta_cong_thuc": "Lợi nhuận trước thuế / Vốn chủ sở hữu bình quân x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "LOI_NHUAN_TRUOC_THUE"},
                        {"ma_bien": "VON_CHU_SO_HUU_BINH_QUAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "LOI_NHUAN_TRUOC_THUE", "ten_bien": "Lợi nhuận trước thuế", "bat_buoc": True},
            {"ma_bien": "VON_CHU_SO_HUU_BINH_QUAN", "ten_bien": "Vốn chủ sở hữu bình quân", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(15.00, 13.00, 10.00, 8.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(14.00, 12.00, 8.00, 6.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(14.00, 12.00, 8.00, 6.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(30.00, 20.00, 15.00, 10.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(14.00, 12.00, 8.00, 6.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(5.00, 4.00, 3.00, 2.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 4.2: Tỷ lệ lợi nhuận trước thuế so với tổng tài sản bình quân (ROA)
    # -------------------------------------------------------------
    ct_4_2 = {
        "_id": "CT_4_2",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_E",
        "ma_chi_tieu": "4.2",
        "ma_chi_tieu_goc": "4.2",
        "ten_chi_tieu": "Tỷ lệ lợi nhuận trước thuế so với tổng tài sản bình quân",
        "mo_ta_cong_thuc": "Lợi nhuận trước thuế / Tổng tài sản bình quân x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "LOI_NHUAN_TRUOC_THUE"},
                        {"ma_bien": "TONG_TAI_SAN_BINH_QUAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "LOI_NHUAN_TRUOC_THUE", "ten_bien": "Lợi nhuận trước thuế", "bat_buoc": True},
            {"ma_bien": "TONG_TAI_SAN_BINH_QUAN", "ten_bien": "Tổng tài sản bình quân", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(1.50, 1.10, 0.80, 0.60)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(1.30, 1.00, 0.70, 0.50)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(1.30, 1.00, 0.70, 0.50)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(5.00, 4.00, 3.00, 2.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(4.00, 3.00, 2.00, 1.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(1.00, 0.70, 0.40, 0.20)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 2,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 4.3: Thu nhập lãi cận biên (NIM)
    # -------------------------------------------------------------
    ct_4_3 = {
        "_id": "CT_4_3",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_E",
        "ma_chi_tieu": "4.3",
        "ma_chi_tieu_goc": "4.3",
        "ten_chi_tieu": "Thu nhập lãi cận biên (NIM)",
        "mo_ta_cong_thuc": "NIM = Thu nhập lãi thuần / Tài sản Có sinh lãi bình quân x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "THU_NHAP_LAI_THUAN"},
                        {"ma_bien": "TAI_SAN_CO_SINH_LAI_BINH_QUAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "THU_NHAP_LAI_THUAN", "ten_bien": "Thu nhập lãi thuần", "bat_buoc": True},
            {"ma_bien": "TAI_SAN_CO_SINH_LAI_BINH_QUAN", "ten_bien": "Tài sản Có sinh lãi bình quân", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(3.00, 2.50, 2.00, 1.50)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(2.80, 2.40, 1.90, 1.40)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(2.80, 2.40, 1.90, 1.40)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(20.00, 15.00, 10.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(8.00, 5.00, 3.50, 2.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(2.40, 2.00, 1.60, 1.20)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 3,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 4.4: Số ngày lãi phải thu
    # -------------------------------------------------------------
    ct_4_4 = {
        "_id": "CT_4_4",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_E",
        "ma_chi_tieu": "4.4",
        "ma_chi_tieu_goc": "4.4",
        "ten_chi_tieu": "Số ngày lãi phải thu",
        "mo_ta_cong_thuc": "Số ngày lãi phải thu = Lãi và phí phải thu x 365 / Thu nhập từ lãi và các khoản tương tự.",
        "cong_thuc": {
            "phep_toan": "CHIA",
            "tham_so": [
                {
                    "phep_toan": "NHAN",
                    "tham_so": [
                        {"ma_bien": "LAI_PHAI_THU"},
                        {"gia_tri": 365}
                    ]
                },
                {"ma_bien": "THU_NHAP_TU_LAI"}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "LAI_PHAI_THU", "ten_bien": "Lãi và phí phải thu", "bat_buoc": True},
            {"ma_bien": "THU_NHAP_TU_LAI", "ten_bien": "Thu nhập từ lãi và các khoản tương tự", "bat_buoc": True}
        ],
        "don_vi_tinh": "ngày",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(55.00, 70.00, 85.00, 95.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(60.00, 75.00, 90.00, 100.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(60.00, 75.00, 90.00, 100.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(20.00, 25.00, 35.00, 50.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(25.00, 30.00, 40.00, 55.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(60.00, 75.00, 90.00, 100.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 4,
        "is_active": 1
    }

    await db.ChiTieu.insert_many([ct_4_1, ct_4_2, ct_4_3, ct_4_4])
    logger.info("Đã nạp 4 chỉ tiêu chính thức nhóm KẾT QUẢ HOẠT ĐỘNG KINH DOANH (E): 4.1 - 4.4!")

    # 3. CẬP NHẬT DỮ LIỆU TÍNH ĐIỂM KỲ 2025 CỦA NH_001
    await db.DuLieuTinhDiem.update_one(
        {"_id": "DL_NH001_2025_V1"},
        {"$set": {
            "du_lieu.LOI_NHUAN_TRUOC_THUE": 1400,
            "du_lieu.VON_CHU_SO_HUU_BINH_QUAN": 10000,
            "du_lieu.TONG_TAI_SAN_BINH_QUAN": 100000,
            "du_lieu.THU_NHAP_LAI_THUAN": 2500,
            "du_lieu.TAI_SAN_CO_SINH_LAI_BINH_QUAN": 90000,
            "du_lieu.LAI_PHAI_THU": 800,
            "du_lieu.THU_NHAP_TU_LAI": 6000
        }}
    )
    logger.info("Đã cập nhật các biến tài chính kinh doanh kỳ 2025 cho NH_001!")

    logger.info("🎉 ĐÃ NẠP THÀNH CÔNG DỮ LIỆU THẬT CHO NHÓM KẾT QUẢ HOẠT ĐỘNG KINH DOANH (E)!")

if __name__ == "__main__":
    asyncio.run(run_load_group_e())
