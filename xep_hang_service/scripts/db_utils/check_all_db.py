import asyncio
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
from app.core.database import connect_to_mongo, get_database, close_mongo_connection

async def check_all():
    await connect_to_mongo()
    db = get_database()
    
    dts = await db.DoiTuongDanhGia.find().to_list(100)
    dls = await db.DuLieuTinhDiem.find({"ky_du_lieu": "2025"}).to_list(100)
    sps = await db.DuLieuSaiPham.find({"ky_du_lieu": "2025"}).to_list(100)
    kqs = await db.KetQuaTinhDiem.find({"ky_du_lieu": "2025"}).to_list(100)

    print("📌 DoiTuongDanhGia trong DB:", [d["_id"] for d in dts])
    print("📌 DuLieuTinhDiem (Kỳ 2025) trong DB:", [d["_id"] for d in dls])
    print("📌 Số bản ghi DuLieuSaiPham (Kỳ 2025):", len(sps))
    print("📌 KetQuaTinhDiem (Kỳ 2025) trong DB:", [(k["_id"], k["tong_diem"], k["xep_hang"]) for k in kqs])
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(check_all())
