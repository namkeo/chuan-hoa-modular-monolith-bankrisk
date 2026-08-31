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

async def seed_sai_pham_collection_standard():
    await connect_to_mongo()
    db = get_database()

    # 1. Làm sạch collection DuLieuSaiPham cũ của NH_001 kỳ 2025
    await db.DuLieuSaiPham.delete_many({"doi_tuong_id": "NH_001", "ky_du_lieu": "2025"})
    logger.info("Đã làm sạch dữ liệu trong collection 'DuLieuSaiPham' cho NH_001 kỳ 2025.")

    # 2. Tạo dữ liệu mẫu sai phạm chuẩn hóa khớp chính xác với ma_hanh_vi_vi_pham (C_DT.a, C_DT.b, C_DT.c, A_DT.g...)
    danh_sach_sai_pham_docs = [
        # --- 1. NHÓM VỐN (C) ---
        {
            "_id": "SP_NH001_2025_C_a",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C",
            "ma_chi_tieu": "C_DT",
            "ma_hanh_vi_vi_pham": "C_DT.a",
            "noi_dung_chi_tiet": "Tuân thủ các quy định pháp luật về ban hành, rà soát, xem xét sửa đổi, bổ sung, báo cáo Quy định nội bộ về đánh giá chất lượng tài sản có và tuân thủ tỷ lệ an toàn vốn tối thiểu theo quy định (Phát hiện từ năm ngoái chưa khắc phục).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": False,
            "phat_hien_4_nam_truoc": True,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": False,
            "muc_phat_tien_quyet_dinh": None,
            "muc_phat_tien_trung_binh": None,
            "so_lan_vi_pham": 1,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_C_b",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C",
            "ma_chi_tieu": "C_DT",
            "ma_hanh_vi_vi_pham": "C_DT.b",
            "noi_dung_chi_tiet": "Tuân thủ tỷ lệ an toàn vốn tối thiểu theo quy định (Mức phạt tiền trung bình 150 triệu VNĐ, vi phạm 3 lần).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 150.0,
            "muc_phat_tien_trung_binh": 150.0,
            "so_lan_vi_pham": 3,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_C_c",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C",
            "ma_chi_tieu": "C_DT",
            "ma_hanh_vi_vi_pham": "C_DT.c",
            "noi_dung_chi_tiet": "Tuân thủ các quy định pháp luật về giá trị thực của vốn điều lệ, vốn được cấp (Mức phạt tiền trung bình 250 triệu VNĐ, vi phạm 5 lần).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 250.0,
            "muc_phat_tien_trung_binh": 250.0,
            "so_lan_vi_pham": 5,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        # --- 2. NHÓM CHẤT LƯỢNG TÀI SẢN (A) ---
        {
            "_id": "SP_NH001_2025_A_g",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "A",
            "ma_chi_tieu": "A_DT",
            "ma_hanh_vi_vi_pham": "A_DT.g",
            "noi_dung_chi_tiet": "Tuân thủ các quy định pháp luật về hạn chế và giới hạn cấp tín dụng (Phạt trung bình 150 triệu VNĐ, 2 lần vi phạm).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 150.0,
            "muc_phat_tien_trung_binh": 150.0,
            "so_lan_vi_pham": 2,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_A_d",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "A",
            "ma_chi_tieu": "A_DT",
            "ma_hanh_vi_vi_pham": "A_DT.d",
            "noi_dung_chi_tiet": "Tuân thủ các quy định pháp luật về phân loại tài sản có, mức trích, phương pháp trích lập dự phòng rủi ro và việc sử dụng dự phòng rủi ro để xử lý rủi ro (Phạt trung bình 250 triệu VNĐ, 1 lần).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 250.0,
            "muc_phat_tien_trung_binh": 250.0,
            "so_lan_vi_pham": 1,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        },
        # --- 3. NHÓM QUẢN TRỊ ĐIỀU HÀNH (M) ---
        {
            "_id": "SP_NH001_2025_M_e",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "M",
            "ma_chi_tieu": "M_DT",
            "ma_hanh_vi_vi_pham": "M_DT.e",
            "noi_dung_chi_tiet": "Tuân thủ các quy định pháp luật về chế độ thông tin, báo cáo (Phạt trung bình 80 triệu VNĐ, 4 lần vi phạm).",
            "co_quan_quan_ly_phat_hien": True,
            "tctd_tu_phat_hien": False,
            "phat_hien_trong_nam_xep_hang": True,
            "phat_hien_4_nam_truoc": False,
            "da_khac_phuc_song": False,
            "co_muc_phat_tien": True,
            "muc_phat_tien_quyet_dinh": 80.0,
            "muc_phat_tien_trung_binh": 80.0,
            "so_lan_vi_pham": 4,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        }
    ]

    await db.DuLieuSaiPham.insert_many(danh_sach_sai_pham_docs)
    logger.info(f"🎉 Đã chèn {len(danh_sach_sai_pham_docs)} bản ghi sai phạm chuẩn hóa (theo mã C_DT.a, A_DT.g...) vào collection 'DuLieuSaiPham'!")

    # 3. Tính toán và ghi đè kết quả chuẩn vào KetQuaTinhDiem
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("NH_001", "2025", luu_ket_qua=True)
    logger.info(f"🎉 TÍNH ĐIỂM THÀNH CÔNG! ID: {res.ket_qua_id} | Tổng điểm: {res.tong_diem} | Xếp hạng: {res.xep_hang}")

    print("\n================ CHI TIẾT ĐIỂM ĐỊNH TÍNH TỪ DỮ LIỆU CẬP NHẬT (loai_chi_tieu=DINH_TINH) ================")
    for nhom in res.ket_qua_cac_nhom:
        print(f"\n📌 NHÓM {nhom.ma_nhom} - {nhom.ten_nhom}:")
        print(f"   - Điểm định lượng: {nhom.diem_dinh_luong} (Trọng số DL: {nhom.trong_so_nhom_dinh_luong}%)")
        print(f"   - Điểm định tính : {nhom.diem_dinh_tinh} (Trọng số DT: {nhom.trong_so_nhom_dinh_tinh}%)")
        print(f"   - Điểm đóng góp  : {nhom.diem_nhom} / {nhom.trong_so_tieu_chi / 100:.2f} điểm")
        for ct in nhom.ket_qua_cac_chi_tieu:
            if "DT" in ct.ma_chi_tieu_duoc_chon:
                print(f"   👉 [{ct.ma_chi_tieu_duoc_chon}] {ct.ten_chi_tieu}: Điểm = {ct.diem_theo_nguong}")
                print(f"      + Diễn giải: {ct.dien_giai}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed_sai_pham_collection_standard())
