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
logger = logging.getLogger("seed_qualitative_c")

def make_muc_diem_dinh_tinh_chung(n1, n2, n3, n4):
    """
    Tạo 5 mức điểm chuẩn định tính áp dụng chung cho mọi TCTD theo Điều 16a TT52/TT23:
    (i) Điểm 5: <= 0.50%
    (ii) Điểm 4: > 0.50% và <= 1.00%
    (iii) Điểm 3: > 1.00% và <= 1.50%
    (iv) Điểm 2: > 1.50% và <= 2.00%
    (v) Điểm 1: > 2.00%
    """
    return [
        {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": n1, "bao_gom_den": True},
        {"thu_tu": 2, "diem": 4, "tu": n1, "bao_gom_tu": False, "den": n2, "bao_gom_den": True},
        {"thu_tu": 3, "diem": 3, "tu": n2, "bao_gom_tu": False, "den": n3, "bao_gom_den": True},
        {"thu_tu": 4, "diem": 2, "tu": n3, "bao_gom_tu": False, "den": n4, "bao_gom_den": True},
        {"thu_tu": 5, "diem": 1, "tu": n4, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
    ]

async def run_load_qualitative_c():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Cập nhật NTC_C để thiết lập rõ trọng số nhóm định tính = 5.0%
    await db.NhomTieuChi.update_one(
        {"_id": "NTC_C"},
        {"$set": {"trong_so_nhom_dinh_tinh": 5.0}}
    )

    # 1. XÓA CHỈ TIÊU ĐỊNH TÍNH C_DT CỦ NẾU CÓ
    await db.ChiTieu.delete_one({"_id": "CT_C_DT"})

    # 2. TẠO CHỈ TIÊU ĐỊNH TÍNH NHÓM VỐN (C)
    # Không dùng công thức, không dùng danh sách biến. Điểm do người dùng đánh giá và nhập trực tiếp.
    ct_c_dt = {
        "_id": "CT_C_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "C_DT",
        "ma_chi_tieu_goc": "C_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm VỐN (C)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Vốn do người dùng/cán bộ thanh tra đánh giá và nhập trực tiếp (từ 1 đến 5 điểm) dựa trên các nội dung tuân thủ và tình hình vi phạm.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {
                "ma_noidung": "a",
                "ten_noidung": "Tuân thủ các quy định pháp luật và ban hành, rà soát, xem xét sửa đổi, bổ sung, báo cáo Quy định nội bộ về đánh giá chất lượng tài sản có và tuân thủ tỷ lệ an toàn vốn tối thiểu theo quy định;"
            },
            {
                "ma_noidung": "b",
                "ten_noidung": "Tuân thủ tỷ lệ an toàn vốn tối thiểu theo quy định;"
            },
            {
                "ma_noidung": "c",
                "ten_noidung": "Tuân thủ các quy định pháp luật và giá trị thực của vốn điều lệ, vốn được cấp;"
            },
            {
                "ma_noidung": "d",
                "ten_noidung": "Tuân thủ các quy định pháp luật về đánh giá nội bộ về mức đủ vốn."
            }
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TUYNH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "ALL",
                "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng",
                "trong_so": 50.0,
                "cac_muc_diem": make_muc_diem_dinh_tinh_chung(0.50, 1.00, 1.50, 2.00)
            }
        ],
        "noi_dung_cham_diem": "Điểm định tính do cán bộ thanh tra/người dùng trực tiếp chấm và nhập vào hệ thống (thang điểm 1 - 5). Dùng điểm thô nhập vào để nhân trọng số quy đổi.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    await db.ChiTieu.insert_one(ct_c_dt)
    logger.info("Đã nạp chỉ tiêu định tính không công thức cho nhóm VỐN (C_DT)!")

    # 3. CẬP NHẬT DỮ LIỆU TÍNH ĐIỂM KỲ 2025 CỦA NH_001
    await db.DuLieuTinhDiem.update_one(
        {"_id": "DL_NH001_2025_V1"},
        {"$set": {
            "du_lieu.C_DT": 5.0
        }}
    )
    logger.info("Đã cập nhật điểm nhập tay C_DT = 5.0 cho NH_001!")

    logger.info("🎉 ĐÃ NẠP THÀNH CÔNG CHỈ TIÊU ĐỊNH TÍNH (KHÔNG CÔNG THỨC/BIẾN) CHO NHÓM VỐN (C)!")

if __name__ == "__main__":
    asyncio.run(run_load_qualitative_c())
