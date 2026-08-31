import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_manager = DatabaseManager()

async def connect_to_mongo():
    logger.info(f"Connecting to MongoDB at {settings.MONGO_URI}...")
    db_manager.client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=300)
    db_manager.db = db_manager.client[settings.MONGO_DB_NAME]
    logger.info(f"Connected to database: {settings.MONGO_DB_NAME}")
    try:
        await create_indexes()
    except Exception as err:
        logger.warn(f"Creating Mongo indexes skipped (MongoDB unreachable): {err}")

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
        logger.info("MongoDB connection closed.")

def get_database() -> AsyncIOMotorDatabase:
    return db_manager.db

async def create_indexes():
    db = get_database()
    if db is None:
        return
    try:
        # BoTieuChi
        await db.BoTieuChi.create_index(
            [("ma_bo_tieu_chi", 1), ("phien_ban", 1)],
            unique=True
        )

        # NhomTieuChi
        await db.NhomTieuChi.create_index(
            [("bo_tieu_chi_id", 1), ("ma_nhom", 1)],
            unique=True
        )

        # ChiTieu
        await db.ChiTieu.create_index(
            [("bo_tieu_chi_id", 1), ("nhom_tieu_chi_id", 1), ("ma_chi_tieu", 1)]
        )
        await db.ChiTieu.create_index(
            [("bo_tieu_chi_id", 1), ("ma_chi_tieu_goc", 1)]
        )

        # DuLieuTinhDiem
        await db.DuLieuTinhDiem.create_index(
            [("doi_tuong_id", 1), ("ky_du_lieu", 1), ("phien_ban", 1)],
            unique=True
        )

        # KetQuaTinhDiem
        await db.KetQuaTinhDiem.create_index(
            [("doi_tuong_id", 1), ("ky_du_lieu", 1)],
            unique=True
        )

        # DoiTuongDanhGia
        await db.DoiTuongDanhGia.create_index(
            [("ma_doi_tuong", 1)],
            unique=True
        )
        # DuLieuSaiPham
        await db.DuLieuSaiPham.create_index(
            [("doi_tuong_id", 1), ("ky_du_lieu", 1), ("ma_nhom_chi_tieu", 1)]
        )
        logger.info("MongoDB indexes created successfully.")
    except Exception as e:
        logger.warning(f"Error creating indexes: {e}")
