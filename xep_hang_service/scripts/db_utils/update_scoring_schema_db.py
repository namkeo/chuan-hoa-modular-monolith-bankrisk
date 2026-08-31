import asyncio
import logging
import sys
from pathlib import Path
from decimal import Decimal

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.utils.decimal_utils import to_decimal, round_decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_database():
    logger.info(f"Connecting to MongoDB: {settings.MONGO_URI} (DB: {settings.MONGO_DB_NAME})")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. Xóa diem_toi_da khỏi collection ChiTieu
    res_ct = await db.ChiTieu.update_many(
        {"diem_toi_da": {"$exists": True}},
        {"$unset": {"diem_toi_da": ""}}
    )
    logger.info(f"ChiTieu updated: {res_ct.modified_count} documents unset diem_toi_da")

    # 2. Xóa diem_toi_da khỏi collection NhomTieuChi
    res_ntc = await db.NhomTieuChi.update_many(
        {"diem_toi_da": {"$exists": True}},
        {"$unset": {"diem_toi_da": ""}}
    )
    logger.info(f"NhomTieuChi updated: {res_ntc.modified_count} documents unset diem_toi_da")

    # 3. Cập nhật các bản ghi trong KetQuaTinhDiem
    cursor = db.KetQuaTinhDiem.find({})
    kq_updated = 0
    async for doc in cursor:
        ket_qua_cac_nhom = doc.get("ket_qua_cac_nhom", [])
        tong_diem_dec = Decimal("0")

        for nhom in ket_qua_cac_nhom:
            if "diem_toi_da" in nhom:
                del nhom["diem_toi_da"]

            tong_diem_quy_doi_nhom = Decimal("0")
            for ct in nhom.get("ket_qua_cac_chi_tieu", []):
                if "diem_toi_da" in ct:
                    del ct["diem_toi_da"]
                
                # Đổi tên diem_tho -> diem_theo_nguong
                if "diem_tho" in ct:
                    ct["diem_theo_nguong"] = ct.pop("diem_tho")

                if ct.get("trang_thai") == "KHONG_AP_DUNG":
                    continue

                val_nguong = ct.get("diem_theo_nguong")
                val_ts = ct.get("trong_so")

                if val_nguong is not None and val_ts is not None:
                    diem_theo_nguong = to_decimal(val_nguong)
                    trong_so = to_decimal(val_ts)
                    diem_quy_doi_dec = round_decimal((diem_theo_nguong * trong_so) / Decimal("100"), 4)
                    ct["diem_quy_doi"] = float(diem_quy_doi_dec)
                    tong_diem_quy_doi_nhom += diem_quy_doi_dec

            diem_nhom_dec = round_decimal(tong_diem_quy_doi_nhom, 4)
            nhom["diem_nhom"] = float(diem_nhom_dec)

            ts_nhom = to_decimal(nhom.get("trong_so_tieu_chi", 0))
            if ts_nhom > 0:
                tong_diem_dec += diem_nhom_dec * (ts_nhom / Decimal("100"))
            else:
                tong_diem_dec += diem_nhom_dec

        tong_diem_rounded = round_decimal(tong_diem_dec, 2)
        
        # Phân loại xếp hạng theo Điều 20
        if tong_diem_dec >= Decimal("4.5"):
            xep_hang = "A"
        elif tong_diem_dec >= Decimal("3.5"):
            xep_hang = "B"
        elif tong_diem_dec >= Decimal("2.5"):
            xep_hang = "C"
        elif tong_diem_dec >= Decimal("1.5"):
            xep_hang = "D"
        else:
            xep_hang = "E"

        await db.KetQuaTinhDiem.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "ket_qua_cac_nhom": ket_qua_cac_nhom,
                    "tong_diem": float(tong_diem_rounded),
                    "xep_hang": xep_hang
                }
            }
        )
        kq_updated += 1

    logger.info(f"KetQuaTinhDiem updated: {kq_updated} documents recalculated and updated to 5-point scale")

    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_database())
