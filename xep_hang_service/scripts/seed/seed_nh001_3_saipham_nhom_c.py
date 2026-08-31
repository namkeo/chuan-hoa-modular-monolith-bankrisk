import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.tinh_diem_service import TinhDiemService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def seed_and_test_nhom_c():
    await connect_to_mongo()
    db = get_database()

    # 1. Xóa dữ liệu sai phạm cũ của NH_001 kỳ 2025 trong collection DuLieuSaiPham
    await db.DuLieuSaiPham.delete_many({"doi_tuong_id": "NH_001", "ky_du_lieu": "2025"})

    # 2. Chèn 3 sai phạm mẫu của NH_001 kỳ 2025 trong Nhóm VỐN (C)
    danh_sach_sai_pham = [
        {
            "_id": "SP_NH001_2025_C_X",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C",
            "ma_chi_tieu": "C_DT",
            "ma_hanh_vi_vi_pham": "C_X",
            "noi_dung_chi_tiet": "Sai phạm X: Vi phạm quy định về ban hành quy định nội bộ đánh giá đủ vốn (từ năm ngoái chưa khắc phục).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": False,
            "phat_hien_4_nam_truoc": True,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": False,
            "muc_phat_tien_quyet_dinh": None,
            "muc_phat_tien_trung_binh": None,
            "so_lan_vi_pham": 1,  # 1 lần -> Lặp lại: 0
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_C_Y",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C",
            "ma_chi_tieu": "C_DT",
            "ma_hanh_vi_vi_pham": "C_Y",
            "noi_dung_chi_tiet": "Sai phạm Y: Vi phạm quy định về tỷ lệ an toàn vốn tối thiểu (Phạt trung bình 150 triệu VNĐ).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 150.0,
            "muc_phat_tien_trung_binh": 150.0,  # >100tr và <=200tr -> Mức điểm 3
            "so_lan_vi_pham": 3,  # 3 lần -> Lặp lại: 3-1 = 2 lần
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_C_Z",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C",
            "ma_chi_tieu": "C_DT",
            "ma_hanh_vi_vi_pham": "C_Z",
            "noi_dung_chi_tiet": "Sai phạm Z: Vi phạm quy định về giá trị thực của vốn điều lệ (Phạt trung bình 250 triệu VNĐ).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 250.0,
            "muc_phat_tien_trung_binh": 250.0,  # >200tr và <=300tr -> Mức điểm 2
            "so_lan_vi_pham": 5,  # 5 lần -> Lặp lại: 5-1 = 4 lần
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        }
    ]

    await db.DuLieuSaiPham.insert_many(danh_sach_sai_pham)
    logger.info("Đã chèn 3 sai phạm mẫu của NH_001 cho Nhóm C vào collection 'DuLieuSaiPham'!")

    # 3. Chạy service tính điểm
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("NH_001", "2025", luu_ket_qua=True)

    print("\n=================== KẾT QUẢ TÍNH ĐIỂM ĐỊNH TÍNH NHÓM C CỦA NH_001 ===================")
    nhom_c = res.ket_qua_cac_nhom[0]
    print(f"📌 Nhóm: {nhom_c.ten_nhom}")
    print(f"   - Điểm định lượng: {nhom_c.diem_dinh_luong} (Trọng số DL: {nhom_c.trong_so_nhom_dinh_luong}%)")
    print(f"   - Điểm định tính : {nhom_c.diem_dinh_tinh} (Trọng số DT: {nhom_c.trong_so_nhom_dinh_tinh}%)")
    print(f"   - Điểm đóng góp  : {nhom_c.diem_nhom} / 0.20 điểm")
    for ct in nhom_c.ket_qua_cac_chi_tieu:
        if ct.ma_chi_tieu_duoc_chon == "C_DT":
            print(f"\n👉 Chi tiết chỉ tiêu định tính C_DT:")
            print(f"   - Điểm theo ngưỡng cuối cùng: {ct.diem_theo_nguong}")
            print(f"   - Diễn giải từng bước       : {ct.dien_giai}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed_and_test_nhom_c())
