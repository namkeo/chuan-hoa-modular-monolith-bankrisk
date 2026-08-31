import asyncio
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.tinh_diem_service import TinhDiemService

async def verify():
    await connect_to_mongo()
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("NH_001", "2025")
    nhom_c = res.ket_qua_cac_nhom[0]
    print(f"Nhóm: {nhom_c.ten_nhom} | Điểm nhóm: {nhom_c.diem_nhom}")
    for ct in nhom_c.ket_qua_cac_chi_tieu:
        print(f" - [{ct.ma_chi_tieu_duoc_chon}] {ct.ten_chi_tieu}: Điểm theo ngưỡng = {ct.diem_theo_nguong} | Điểm quy đổi = {ct.diem_quy_doi} | Diễn giải: {ct.dien_giai}")
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(verify())
