import sys
import asyncio

sys.path.insert(0, ".")

from app.core.database import connect_to_mongo
from app.services.tinh_diem_service import TinhDiemService
from app.repositories.du_lieu_tinh_diem_repository import DuLieuTinhDiemRepository

async def run_batch():
    await connect_to_mongo()
    service = TinhDiemService()
    dl_repo = DuLieuTinhDiemRepository()
    
    records = await dl_repo.find_many({'is_active': 1}, limit=10000)
    print(f"Bat dau tinh lai toan bo {len(records)} ban ghi...")
    
    success = 0
    errors = 0
    for idx, r in enumerate(records):
        doi_tuong_id = r.get("doi_tuong_id")
        ky = r.get("ky_du_lieu")
        if not doi_tuong_id or not ky:
            continue
        try:
            await service.thuc_hien_tinh_diem(
                doi_tuong_id=doi_tuong_id,
                ky_du_lieu=ky,
                luu_ket_qua=True,
                nguoi_tinh="batch_fix"
            )
            success += 1
        except Exception as e:
            errors += 1
            print(f"Error {doi_tuong_id} {ky}: {e}")
            
        if (idx + 1) % 500 == 0:
            print(f"Da xu ly {idx + 1}/{len(records)} ban ghi...")
            
    print(f"Hoan thanh: {success} thanh cong, {errors} that bai.")

if __name__ == "__main__":
    asyncio.run(run_batch())
