import asyncio
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def verify():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    docs = await db.KetQuaTinhDiem.find({}).to_list(100)
    print(f"Total documents in KetQuaTinhDiem: {len(docs)}")
    for d in docs:
        print(f" - ID: {d['_id']} | Đối tượng: {d.get('doi_tuong_id')} | Kỳ: {d.get('ky_du_lieu')} | Tổng điểm: {d.get('tong_diem')} | Xếp hạng: {d.get('xep_hang')}")
    client.close()

if __name__ == "__main__":
    asyncio.run(verify())
