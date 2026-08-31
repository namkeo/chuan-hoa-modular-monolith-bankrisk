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
logger = logging.getLogger("seed_group_s")

def make_muc_diem_cang_nho_cang_tot(n1, n2, n3, n4):
    """
    Tạo 5 mức điểm cho chỉ tiêu CÀNG TIỆM CẬN 0 / CÀNG NHỎ CÀNG TỐT:
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

async def run_load_group_s():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. NẠP NHÓM 6: MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (S)
    nhom_s = {
        "_id": "NTC_S",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "S",
        "so_thu_tu": 6,
        "ten_nhom": "MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (S)",
        "trong_so_tieu_chi": 5.0,
        "trong_so_nhom_dinh_luong": 2.0,
        "thu_tu_hien_thi": 6,
        "ghi_chu": "Trọng số tiêu chí: 5,00%; trọng số nhóm định lượng: 2,00%",
        "is_active": 1
    }
    await db.NhomTieuChi.replace_one({"_id": "NTC_S"}, nhom_s, upsert=True)
    logger.info("Đã nạp NhomTieuChi: NTC_S (MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG)")

    # 2. XÓA CÁC CHỈ TIÊU CỦA NHÓM S NẾU CÓ
    await db.ChiTieu.delete_many({"nhom_tieu_chi_id": "NTC_S"})

    # -------------------------------------------------------------
    # Chỉ tiêu 6.1: Tỷ lệ tổng trạng thái ngoại tệ so với vốn tự có riêng lẻ bình quân
    # -------------------------------------------------------------
    ct_6_1 = {
        "_id": "CT_6_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_S",
        "ma_chi_tieu": "6.1",
        "ma_chi_tieu_goc": "6.1",
        "ten_chi_tieu": "Tỷ lệ tổng trạng thái ngoại tệ so với vốn tự có riêng lẻ bình quân",
        "mo_ta_cong_thuc": "Tỷ lệ tổng trạng thái ngoại tệ so với vốn tự có riêng lẻ bình quân theo tháng.",
        "cong_thuc": {
            "phep_toan": "GIA_TRI_TUYET_DOI",
            "tham_so": [
                {"ma_bien": "TY_LE_TRANG_THAI_NGOAI_TE"}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "TY_LE_TRANG_THAI_NGOAI_TE", "ten_bien": "Tỷ lệ tổng trạng thái ngoại tệ theo tháng", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 15.00, 20.00, 25.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 15.00, 20.00, 25.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(10.00, 15.00, 20.00, 25.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # Chỉ tiêu 6.2: Tỷ lệ chênh lệch tài sản nhạy cảm lãi suất và nợ nhạy cảm lãi suất so với vốn chủ sở hữu
    # -------------------------------------------------------------
    ct_6_2 = {
        "_id": "CT_6_2",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_S",
        "ma_chi_tieu": "6.2",
        "ma_chi_tieu_goc": "6.2",
        "ten_chi_tieu": "Tỷ lệ chênh lệch giữa tài sản nhạy cảm lãi suất và nợ phải trả nhạy cảm lãi suất so với Vốn chủ sở hữu",
        "mo_ta_cong_thuc": "Tỷ lệ = |Tài sản nhạy cảm lãi suất - Nợ phải trả nhạy cảm lãi suất| / Vốn chủ sở hữu x 100%.",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {
                            "phep_toan": "GIA_TRI_TUYET_DOI",
                            "tham_so": [
                                {
                                    "phep_toan": "TRU",
                                    "tham_so": [
                                        {"ma_bien": "TAI_SAN_NHAY_CAM_LAI_SUAT"},
                                        {"ma_bien": "NO_NHAY_CAM_LAI_SUAT"}
                                    ]
                                }
                            ]
                        },
                        {"ma_bien": "VON_CHU_SO_HUU"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "TAI_SAN_NHAY_CAM_LAI_SUAT", "ten_bien": "Tài sản nhạy cảm lãi suất", "bat_buoc": True},
            {"ma_bien": "NO_NHAY_CAM_LAI_SUAT", "ten_bien": "Nợ phải trả nhạy cảm lãi suất", "bat_buoc": True},
            {"ma_bien": "VON_CHU_SO_HUU", "ten_bien": "Vốn chủ sở hữu", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(50.00, 65.00, 80.00, 95.00)
            },
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô nhỏ",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(55.00, 70.00, 85.00, 100.00)
            },
            {
                "ma_loai_doi_tuong": "CHI_NHANH_NGAN_HANG_NUOC_NGOAI",
                "ten_loai_doi_tuong": "Chi nhánh ngân hàng nước ngoài",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(80.00, 90.00, 100.00, 120.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(55.00, 70.00, 85.00, 100.00)
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_CHO_THUE_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty cho thuê tài chính",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(80.00, 90.00, 100.00, 120.00)
            },
            {
                "ma_loai_doi_tuong": "NGAN_HANG_HOP_TAC_XA",
                "ten_loai_doi_tuong": "Ngân hàng hợp tác xã",
                "trong_so": 100.0,
                "cac_muc_diem": make_muc_diem_cang_nho_cang_tot(70.00, 80.00, 90.00, 100.00)
            }
        ],
        "noi_dung_cham_diem": "(i) Điểm 5 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 1; (ii) Điểm 4 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 2 và lớn hơn ngưỡng 1; (iii) Điểm 3 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 3 và lớn hơn ngưỡng 2; (iv) Điểm 2 nếu giá trị tuyệt đối của chỉ tiêu nhỏ hơn hoặc bằng ngưỡng 4 và lớn hơn ngưỡng 3.",
        "can_cu_phap_ly": "TT52 đã được sửa đổi, bổ sung bởi TT23.",
        "thu_tu_hien_thi": 2,
        "is_active": 1
    }

    await db.ChiTieu.insert_many([ct_6_1, ct_6_2])
    logger.info("Đã nạp 2 chỉ tiêu chính thức nhóm MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (S): 6.1 - 6.2!")

    # 3. CẬP NHẬT DỮ LIỆU TÍNH ĐIỂM KỲ 2025 CỦA NH_001
    await db.DuLieuTinhDiem.update_one(
        {"_id": "DL_NH001_2025_V1"},
        {"$set": {
            "du_lieu.TY_LE_TRANG_THAI_NGOAI_TE": 6.5,
            "du_lieu.TAI_SAN_NHAY_CAM_LAI_SUAT": 60000,
            "du_lieu.NO_NHAY_CAM_LAI_SUAT": 55000,
            "du_lieu.VON_CHU_SO_HUU": 12000
        }}
    )
    logger.info("Đã cập nhật các biến nhạy cảm thị trường kỳ 2025 cho NH_001!")

    logger.info("🎉 ĐÃ NẠP THÀNH CÔNG DỮ LIỆU THẬT CHO NHÓM MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (S)!")

if __name__ == "__main__":
    asyncio.run(run_load_group_s())
