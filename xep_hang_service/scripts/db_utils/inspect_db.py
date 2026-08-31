import asyncio
import sys
import io
import json
from motor.motor_asyncio import AsyncIOMotorClient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def main():
    client = AsyncIOMotorClient('mongodb://admin:12345678@localhost:27017/')
    db = client['credit_scoring_db']
    doc = await db.KetQuaTinhDiem.find_one(sort=[('ngay_tinh', -1)])
    if doc:
        for n in doc['ket_qua_cac_nhom']:
            if n['ma_nhom'] == 'C':
                print("KẾT QUẢ NHÓM VỐN (C):")
                print(json.dumps(n, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
