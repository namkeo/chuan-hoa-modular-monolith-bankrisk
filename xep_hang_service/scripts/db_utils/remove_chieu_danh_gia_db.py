import asyncio
import logging
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def remove_chieu_danh_gia_from_db():
    logger.info(f"Connecting to MongoDB: {settings.MONGO_URI} (DB: {settings.MONGO_DB_NAME})")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]
    
    result = await db.ChiTieu.update_many(
        {"chieu_danh_gia": {"$exists": True}},
        {"$unset": {"chieu_danh_gia": ""}}
    )
    logger.info(f"Successfully updated ChiTieu collection. Matched: {result.matched_count}, Modified: {result.modified_count}")
    client.close()

if __name__ == "__main__":
    asyncio.run(remove_chieu_danh_gia_from_db())
