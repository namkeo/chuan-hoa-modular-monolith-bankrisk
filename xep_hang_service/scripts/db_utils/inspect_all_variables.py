import asyncio
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
from app.core.database import connect_to_mongo, get_database, close_mongo_connection

async def inspect_vars():
    await connect_to_mongo()
    db = get_database()
    
    cts = await db.ChiTieu.find({"loai_chi_tieu": {"$ne": "DINH_TINH"}}).to_list(100)
    print(f"Tìm thấy {len(cts)} chỉ tiêu định lượng:")
    for ct in cts:
        print(f"👉 [{ct.get('ma_chi_tieu')}] {ct.get('ten_chi_tieu')}: Các biến = {ct.get('danh_sach_bien')}")
        
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(inspect_vars())
