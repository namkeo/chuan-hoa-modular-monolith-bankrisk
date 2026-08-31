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
logger = logging.getLogger("seed_group_l")

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

async def run_load_group_l():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. NẠP NHÓM 5: KHẢ NĂNG THANH KHOẢN (L)
    nhom_l = {
        "_id": "NTC_L",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "L",
        "so_thu_tu": 5,
        "ten_nhom": "KHẢ NĂNG THANH KHOẢN (L)",
        "trong_so_tieu_chi": 15.0,
        "trong_so_nhom_dinh_luong": 10.0,
        "thu_tu_hien_thi": 5,
        "ghi_chu": "Trọng số tiêu chí: 15,00%; trọng số nhóm định lượng: 10,00%",
        "is_active": 1
    }
    await db.NhomTieuChi.replace_one({"_id": "NTC_L"}, nhom_l, upsert=True)
    logger.info("Đã nạp NhomTieuChi: NTC_L (KHẢ NĂNG THANH KHOẢN)")

    # 2. XÓA CÁC CHỈ TIÊU CỦA NHÓM L NẾU CÓ
    await db.ChiTieu.delete_many({"nhom_tieu_chi_id": "NTC_L"})

    # -------------------------------------------------------------
    # Chỉ tiêu 5.1: Tỷ lệ tài sản có tính thanh khoản cao bình quân
    # -------------------------------------------------------------
    ct_5_1 = {
        "_id": "CT_5_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_L",
        "ma_chi_tieu": "5.1",
        "ma_chi_tieu_goc": "5.1",
        "ten_chi_tieu": "Tỷ lệ tài sản có tính thanh khoản cao bình quân so với tổng tài sản bình quân",
        "mo_ta_cong_thuc": "Tài sản có tính thanh khoản cao bình quân / Tổng tài sản bình quân x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN"},
                        {"ma_bien": "TONG_TAI_SAN_BINH_QUAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN", "ten_bien": "Tài sản có tính thanh khoản cao bình quân", "bat_buoc": True},
            {"ma_bien": "TONG_TAI_SAN_BINH_QUAN", "ten_bien": "Tổng tài sản bình quân", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 25.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(20.00, 15.00, 9.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(18.00, 14.00, 8.00, 4.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(25.00, 20.00, 15.00, 10.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(20.00, 15.00, 10.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 40.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(18.00, 14.00, 8.00, 5.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_lon_cang_tot(16.00, 13.00, 8.00, 4.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 2 và nhỏ hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 3 và nhỏ hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu lớn hơn hoặc bằng ngưỡng 4 và nhỏ hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 5.2: Tỷ lệ nguồn vốn ngắn hạn cho vay trung và dài hạn
    # -------------------------------------------------------------
    ct_5_2 = {
        "_id": "CT_5_2",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_L",
        "ma_chi_tieu": "5.2",
        "ma_chi_tieu_goc": "5.2",
        "ten_chi_tieu": "Tỷ lệ nguồn vốn ngắn hạn được sử dụng để cho vay trung và dài hạn",
        "mo_ta_cong_thuc": "Nguồn vốn ngắn hạn được sử dụng để cho vay trung và dài hạn / Nguồn vốn ngắn hạn x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN"},
                        {"ma_bien": "NGUON_VON_NGAN_HAN"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN", "ten_bien": "Nguồn vốn ngắn hạn sử dụng cho vay trung dài hạn", "bat_buoc": True},
            {"ma_bien": "NGUON_VON_NGAN_HAN", "ten_bien": "Nguồn vốn ngắn hạn", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 25.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(25.00, 30.00, 35.00, 40.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(30.00, 35.00, 40.00, 45.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(30.00, 35.00, 40.00, 45.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 60.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(40.00, 70.00, 90.00, 100.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 60.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(40.00, 70.00, 90.00, 100.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(30.00, 35.00, 40.00, 45.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 2,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 5.3: Tỷ lệ dư nợ cho vay so với tổng tiền gửi (LDR)
    # -------------------------------------------------------------
    ct_5_3 = {
        "_id": "CT_5_3",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_L",
        "ma_chi_tieu": "5.3",
        "ma_chi_tieu_goc": "5.3",
        "ten_chi_tieu": "Tỷ lệ dư nợ cho vay so với tổng tiền gửi",
        "mo_ta_cong_thuc": "Dư nợ cho vay / Tổng tiền gửi x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "DU_NO_CHO_VAY"},
                        {"ma_bien": "TONG_TIEN_GUI"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "DU_NO_CHO_VAY", "ten_bien": "Dư nợ cho vay", "bat_buoc": True},
            {"ma_bien": "TONG_TIEN_GUI", "ten_bien": "Tổng tiền gửi", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(70.00, 80.00, 90.00, 95.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(60.00, 70.00, 80.00, 90.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 30.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(70.00, 80.00, 90.00, 95.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(60.00, 70.00, 80.00, 90.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 3,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 5.4: Tỷ lệ tiền gửi của khách hàng có số dư lớn
    # -------------------------------------------------------------
    ct_5_4 = {
        "_id": "CT_5_4",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_L",
        "ma_chi_tieu": "5.4",
        "ma_chi_tieu_goc": "5.4",
        "ten_chi_tieu": "Tỷ lệ tiền gửi của khách hàng có số dư tiền gửi lớn so với tổng tiền gửi",
        "mo_ta_cong_thuc": "Tiền gửi của khách hàng có số dư tiền gửi lớn / Tổng tiền gửi x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "TIEN_GUI_KHACH_HANG_LON"},
                        {"ma_bien": "TONG_TIEN_GUI"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "TIEN_GUI_KHACH_HANG_LON", "ten_bien": "Tiền gửi của khách hàng có số dư lớn", "bat_buoc": True},
            {"ma_bien": "TONG_TIEN_GUI", "ten_bien": "Tổng tiền gửi", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(5.00, 10.00, 13.00, 18.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(7.00, 12.00, 15.00, 20.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(30.00, 40.00, 50.00, 60.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 20.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(7.00, 12.00, 15.00, 20.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 4,
        "is_active": 1
    }

    await db.ChiTieu.insert_many([ct_5_1, ct_5_2, ct_5_3, ct_5_4])
    logger.info("Đã nạp 4 chỉ tiêu chính thức nhóm KHẢ NĂNG THANH KHOẢN (L): 5.1 - 5.4!")

    # 3. CẬP NHẬT DỮ LIỆU TÍNH ĐIỂM KỲ 2025 CỦA NH_001
    await db.DuLieuTinhDiem.update_one(
        {"_id": "DL_NH001_2025_V1"},
        {"$set": {
            "du_lieu.TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 18000,
            "du_lieu.VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 5000,
            "du_lieu.NGUON_VON_NGAN_HAN": 20000,
            "du_lieu.DU_NO_CHO_VAY": 40000,
            "du_lieu.TONG_TIEN_GUI": 55000,
            "du_lieu.TIEN_GUI_KHACH_HANG_LON": 4000
        }}
    )
    logger.info("Đã cập nhật các biến thanh khoản kỳ 2025 cho NH_001!")

    logger.info("🎉 ĐÃ NẠP THÀNH CÔNG DỮ LIỆU THẬT CHO NHÓM KHẢ NĂNG THANH KHOẢN (L)!")

if __name__ == "__main__":
    asyncio.run(run_load_group_l())
