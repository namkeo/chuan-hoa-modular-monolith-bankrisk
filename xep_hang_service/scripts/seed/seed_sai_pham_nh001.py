import asyncio
import logging
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.tinh_diem_service import TinhDiemService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_sai_pham_and_recalculate():
    await connect_to_mongo()
    db = get_database()

    # Danh sách dữ liệu sai phạm chi tiết kỳ 2025 cho NH_001
    danh_sach_sai_pham = [
        # 1. NHÓM VỐN (C)
        {
            "ma_nhom_chi_tieu": "C",
            "ma_hanh_vi_vi_pham": "C_1.a",
            "noi_dung_chi_tiet": "Chưa rà soát, sửa đổi kịp thời quy định nội bộ về đánh giá chất lượng tài sản có theo Thông tư 23/2023/TT-NHNN.",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": False,
            "muc_phat_tien_quyet_dinh": None,
            "muc_phat_tien_trung_binh": None,
            "so_lan_vi_pham": 1
        },
        # 2. NHÓM CHẤT LƯỢNG TÀI SẢN (A)
        {
            "ma_nhom_chi_tieu": "A",
            "ma_hanh_vi_vi_pham": "A_2.g",
            "noi_dung_chi_tiet": "Vi phạm quy định về giới hạn cấp tín dụng đối với một khách hàng và người có liên quan.",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 150.0,
            "muc_phat_tien_trung_binh": 150.0,
            "so_lan_vi_pham": 2
        },
        {
            "ma_nhom_chi_tieu": "A",
            "ma_hanh_vi_vi_pham": "A_2.d",
            "noi_dung_chi_tiet": "Phân loại nợ chưa chính xác đối với một số khoản vay thuộc nhóm nợ cần chú ý.",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 250.0,
            "muc_phat_tien_trung_binh": 250.0,
            "so_lan_vi_pham": 1
        },
        # 3. NHÓM QUẢN TRỊ ĐIỀU HÀNH (M)
        {
            "ma_nhom_chi_tieu": "M",
            "ma_hanh_vi_vi_pham": "M_3.e",
            "noi_dung_chi_tiet": "Chậm gửi báo cáo thống kê định kỳ theo quy định của Ngân hàng Nhà nước.",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 80.0,
            "muc_phat_tien_trung_binh": 80.0,
            "so_lan_vi_pham": 4
        }
    ]

    # Cập nhật danh sách sai phạm vào DuLieuTinhDiem cho NH_001 kỳ 2025
    result = await db.DuLieuTinhDiem.update_one(
        {"doi_tuong_id": "NH_001", "ky_du_lieu": "2025"},
        {"$set": {
            "danh_sach_sai_pham": danh_sach_sai_pham,
            "du_lieu.danh_sach_sai_pham": danh_sach_sai_pham
        }}
    )
    logger.info(f"Đã cập nhật danh sách sai phạm vào DuLieuTinhDiem cho NH_001 (Modified: {result.modified_count})")

    # Thực hiện tính điểm lại cho NH_001
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("NH_001", "2025", luu_ket_qua=True)
    logger.info(f"🎉 TÍNH ĐIỂM THÀNH CÔNG CHO NH_001! Tổng điểm: {res.tong_diem} | Xếp hạng: {res.xep_hang}")

    print("\n================ CHI TIẾT ĐIỂM ĐỊNH TÍNH VÀ ĐỊNH LƯỢNG NĂM 2025 CỦA NH_001 ================")
    for nhom in res.ket_qua_cac_nhom:
        print(f"\n📌 NHÓM {nhom.ma_nhom} - {nhom.ten_nhom}:")
        print(f"   - Điểm định lượng: {nhom.diem_dinh_luong} (Trọng số định lượng: {nhom.trong_so_nhom_dinh_luong}%)")
        print(f"   - Điểm định tính : {nhom.diem_dinh_tinh} (Trọng số định tính : {nhom.trong_so_nhom_dinh_tinh}%)")
        print(f"   - Điểm nhóm      : {nhom.diem_nhom} / {nhom.trong_so_tieu_chi / 100:.2f} điểm đóng góp")
        for ct in nhom.ket_qua_cac_chi_tieu:
            if "DT" in ct.ma_chi_tieu_duoc_chon:
                print(f"   👉 [CHỈ TIÊU ĐỊNH TÍNH {ct.ma_chi_tieu_duoc_chon}] {ct.ten_chi_tieu}:")
                print(f"      + Điểm theo ngưỡng: {ct.diem_theo_nguong}")
                print(f"      + Diễn giải       : {ct.dien_giai}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed_sai_pham_and_recalculate())
