import asyncio
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
from app.core.database import connect_to_mongo, get_database, close_mongo_connection

async def main():
    await connect_to_mongo()
    db = get_database()
    doc = await db.ChiTieu.find_one({"_id": "CT_1_1_A"})
    if doc:
        print("Mã chỉ tiêu:", doc.get("ma_chi_tieu"))
        print("Cấu hình theo đối tượng:", doc.get("cau_hinh_theo_doi_tuong"))
    else:
        print("Không tìm thấy CT_1_1_A")
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
