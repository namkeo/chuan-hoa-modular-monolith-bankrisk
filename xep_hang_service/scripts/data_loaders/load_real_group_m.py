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
logger = logging.getLogger("seed_group_m")

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

async def run_load_group_m():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. NẠP NHÓM 3: QUẢN TRỊ ĐIỀU HÀNH (M)
    nhom_m = {
        "_id": "NTC_M",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "M",
        "so_thu_tu": 3,
        "ten_nhom": "QUẢN TRỊ ĐIỀU HÀNH (M)",
        "trong_so_tieu_chi": 10.0,
        "trong_so_nhom_dinh_luong": 3.0,
        "thu_tu_hien_thi": 3,
        "ghi_chu": "Trọng số tiêu chí: 10,00%; trọng số nhóm định lượng: 3,00%",
        "is_active": 1
    }
    await db.NhomTieuChi.replace_one({"_id": "NTC_M"}, nhom_m, upsert=True)
    logger.info("Đã nạp NhomTieuChi: NTC_M (QUẢN TRỊ ĐIỀU HÀNH)")

    # 2. XÓA CÁC CHỈ TIÊU CỦA NHÓM M NẾU CÓ
    await db.ChiTieu.delete_many({"nhom_tieu_chi_id": "NTC_M"})

    # -------------------------------------------------------------
    # Chỉ tiêu 3.1: Tỷ lệ chi phí hoạt động so với tổng thu nhập hoạt động (CIR)
    # -------------------------------------------------------------
    ct_3_1 = {
        "_id": "CT_3_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_M",
        "ma_chi_tieu": "3.1",
        "ma_chi_tieu_goc": "3.1",
        "ten_chi_tieu": "Tỷ lệ chi phí hoạt động so với tổng thu nhập hoạt động",
        "mo_ta_cong_thuc": "Chi phí hoạt động / Tổng thu nhập hoạt động x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "CHI_PHI_HOAT_DONG"},
                        {"ma_bien": "TONG_THU_NHAP_HOAT_DONG"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "CHI_PHI_HOAT_DONG", "ten_bien": "Chi phí hoạt động", "bat_buoc": True},
            {"ma_bien": "TONG_THU_NHAP_HOAT_DONG", "ten_bien": "Tổng thu nhập hoạt động", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(35.00, 45.00, 50.00, 60.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(40.00, 50.00, 60.00, 70.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(40.00, 50.00, 60.00, 70.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(25.00, 35.00, 45.00, 55.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(25.00, 35.00, 45.00, 55.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(40.00, 50.00, 60.00, 70.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    await db.ChiTieu.insert_one(ct_3_1)
    logger.info("Đã nạp chỉ tiêu 3.1 cho nhóm QUẢN TRỊ ĐIỀU HÀNH (M)!")

    # 3. CẬP NHẬT DỮ LIỆU TÍNH ĐIỂM KỲ 2025 CỦA NH_001
    await db.DuLieuTinhDiem.update_one(
        {"_id": "DL_NH001_2025_V1"},
        {"$set": {
            "du_lieu.CHI_PHI_HOAT_DONG": 4200,
            "du_lieu.TONG_THU_NHAP_HOAT_DONG": 10000
        }}
    )
    logger.info("Đã cập nhật biến CHI_PHI_HOAT_DONG và TONG_THU_NHAP_HOAT_DONG cho NH_001!")

    logger.info("🎉 ĐÃ NẠP THÀNH CÔNG DỮ LIỆU THẬT CHO NHÓM QUẢN TRỊ ĐIỀU HÀNH (M)!")

if __name__ == "__main__":
    asyncio.run(run_load_group_m())
