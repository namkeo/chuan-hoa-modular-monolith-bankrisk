import asyncio
import sys

# Ensure UTF-8 output encoding for console
sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.tinh_diem_service import TinhDiemService

async def main():
    await connect_to_mongo()
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("NH_001", "2025")
    print("=== KẾT QUẢ TÍNH ĐIỂM SANG MONGODB ===")
    print(res.model_dump_json(indent=2))
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
