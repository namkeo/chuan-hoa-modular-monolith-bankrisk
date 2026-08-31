import asyncio
import logging
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.tinh_diem_service import TinhDiemService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Full sample data for test bank NH_001 & NH_002 kỳ 2025
SAMPLE_FULL_INPUT_DATA = {
    # Nhóm C
    "C": 10000,
    "RWA": 90000,
    "KOR": 100,
    "KMR": 50,
    "VON_CAP_1": 8500,
    "VON_TU_CO": 10000,
    "TONG_TAI_SAN_CO_RUI_RO": 90000,
    "C_DT": 5.0,

    # Nhóm A
    "NO_XAU": 900,
    "NO_XAU_VAMC_CHUA_XU_LY": 100,
    "NO_CO_TIEM_AN_THANH_NO_XAU": 120,
    "TONG_NO": 40000,
    "NO_NHOM_2": 1280,
    "DU_NO_KHACH_HANG_LON": 10000,
    "DU_NO_TO_CHUC_CA_NHAN": 50000,
    "NO_NGOAI_BANG_3_5": 200,
    "TONG_NO_NGOAI_BANG_1_5": 42000,
    "DU_PHONG_CHUNG_KHOAN": 150,
    "TONG_SO_DU_CHUNG_KHOAN": 10000,
    "DU_NO_BAT_DONG_SAN": 3500,
    "TONG_DU_NO_TIN_DUNG": 40000,
    "DU_PHONG_CU_THE_DA_TRICH": 1200,
    "DU_PHONG_CHUNG_DA_TRICH": 800,
    "TRICH_LAP_CON_THIEU": 0,
    "LAI_PHI_PAI_THU_CHUA_THU_DUOC": 400,
    "TAI_SAN_CO_KHAC": 5000,
    "DU_NO_LIEN_KET_BAT_DONG_SAN": 8000,
    "DU_NO_CHUNG_KHOAN": 1500,
    "DU_NO_TRAI_PHIEU_DOANH_NGHIEP": 3000,
    "DU_NO_TAP_DOAN_LON": 12000,
    "A_DT": 4.0,

    # Nhóm M
    "CHI_PHI_HOAT_DONG": 2500,
    "TONG_THU_NHAP_HOAT_DONG": 6000,
    "M_DT": 4.0,

    # Nhóm E
    "LOI_NHUAN_TRUOC_THUE": 2000,
    "LOI_NHUAN_SAU_THUE": 1800,
    "VON_CHU_SO_HUU": 12000,
    "VON_CHU_SO_HUU_BINH_QUAN": 11500,
    "TONG_TAI_SAN_BINH_QUAN": 110000,
    "THU_NHAP_LAI_THUAN": 4500,
    "TAI_SAN_CO_SINH_LAI_BINH_QUAN": 95000,
    "LAI_PHAI_THU": 400,
    "THU_NHAP_TU_LAI": 5000,
    "THU_NHAP_NGOAI_LAI": 1500,
    "SO_NGAY_QUA_HAN_NOP_BAO_CAO": 0,
    "E_DT": 5.0,

    # Nhóm L
    "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 25000,
    "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 22500,
    "NGUON_VON_NGAN_HAN": 100000,
    "TAI_SAN_CO_THANH_KHOAN": 25000,
    "TONG_TAI_SAN": 115000,
    "NGUON_VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 22.5,
    "DU_NO_CHO_VAY": 40000,
    "TONG_TIEN_GUI": 55000,
    "TIEN_GUI_KHACH_HANG_LON": 4000,
    "L_DT": 4.0,

    # Nhóm S
    "TY_LE_TRANG_THAI_NGOAI_TE": 6.5,
    "TAI_SAN_NHAY_CAM_LAI_SUAT": 60000,
    "NO_NHAY_CAM_LAI_SUAT": 55000,
    "S_DT": 5.0
}

async def main():
    await connect_to_mongo()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    service = TinhDiemService()

    # 1. Cập nhật dữ liệu đầu vào đầy đủ cho DuLieuTinhDiem cho cả NH_001 và NH_002
    await db.DuLieuTinhDiem.update_one(
        {"doi_tuong_id": "NH_001", "ky_du_lieu": "2025"},
        {
            "$set": {
                "du_lieu": SAMPLE_FULL_INPUT_DATA,
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "thuoc_tinh": {"ap_dung_thong_tu_41": True},
                "trang_thai": "DA_PHE_DUYET",
                "is_active": 1
            }
        },
        upsert=True
    )

    await db.DuLieuTinhDiem.update_one(
        {"doi_tuong_id": "NH_002", "ky_du_lieu": "2025"},
        {
            "$set": {
                "du_lieu": SAMPLE_FULL_INPUT_DATA,
                "ma_loai_doi_tuong": "NHTM_QUY_MO_NHO",
                "thuoc_tinh": {"ap_dung_thong_tu_41": False},
                "trang_thai": "DA_PHE_DUYET",
                "is_active": 1
            }
        },
        upsert=True
    )
    logger.info("Đã cập nhật đầy đủ dữ liệu đầu vào cho NH_001 và NH_002 kỳ 2025")

    # 2. Xóa các bản ghi cũ/trùng lặp trong KetQuaTinhDiem
    await db.KetQuaTinhDiem.delete_many({})
    logger.info("Đã làm sạch KetQuaTinhDiem")

    # 3. Tính toán và lưu duy nhất 1 bản ghi cho mỗi (doi_tuong_id, ky_du_lieu)
    du_lieu_cursor = db.DuLieuTinhDiem.find({"is_active": 1})
    du_lieu_list = await du_lieu_cursor.to_list(length=100)

    processed_keys = set()
    for dl in du_lieu_list:
        doi_tuong_id = dl["doi_tuong_id"]
        ky_du_lieu = dl["ky_du_lieu"]
        key = (doi_tuong_id, ky_du_lieu)

        if key in processed_keys:
            continue
        processed_keys.add(key)

        logger.info(f"Đang thực hiện tính điểm cho đối tượng {doi_tuong_id} - Kỳ {ky_du_lieu}...")
        try:
            res = await service.thuc_hien_tinh_diem(
                doi_tuong_id=doi_tuong_id,
                ky_du_lieu=ky_du_lieu,
                luu_ket_qua=True
            )
            logger.info(f"Thành công! ID: {res.ket_qua_id} | Tổng điểm: {res.tong_diem} | Xếp hạng: {res.xep_hang}")
        except Exception as e:
            logger.error(f"Lỗi tính điểm cho {doi_tuong_id} - Kỳ {ky_du_lieu}: {e}")

    # 4. Đếm số lượng bản ghi trong KetQuaTinhDiem
    count = await db.KetQuaTinhDiem.count_documents({})
    logger.info(f"==> Tổng số bản ghi duy nhất trong KetQuaTinhDiem: {count}")

    # Hiển thị tất cả bản ghi duy nhất trong DB
    cursor = db.KetQuaTinhDiem.find({})
    async for doc in cursor:
        logger.info(f"Bản ghi duy nhất trong DB: ID={doc['_id']}, doi_tuong={doc['doi_tuong_id']}, ky={doc['ky_du_lieu']}, tong_diem={doc['tong_diem']}, xep_hang={doc['xep_hang']}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
