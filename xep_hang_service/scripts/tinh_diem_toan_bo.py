import asyncio
import sys
import os
import time

# Ensure be directory is in sys.path
be_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if be_dir not in sys.path:
    sys.path.insert(0, be_dir)

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import connect_to_mongo
from app.services.tinh_diem_service import TinhDiemService
from app.repositories.du_lieu_tinh_diem_repository import DuLieuTinhDiemRepository

async def main():
    print("============================================================")
    print("  HỆ THỐNG TÍNH ĐIỂM XẾP HẠNG TÍN NHIỆM TỔ CHỨC TÍN DỤNG (KTNN)")
    print("  Lệnh: Tính điểm cho toàn bộ bản ghi trong DuLieuTinhDiem")
    print("============================================================")
    
    start_time = time.time()
    await connect_to_mongo()
    
    dl_repo = DuLieuTinhDiemRepository()
    service = TinhDiemService()
    
    records = await dl_repo.find_many({"is_active": 1}, limit=10000)
    total_records = len(records)
    print(f"[*] Tìm thấy {total_records} bản ghi dữ liệu tính điểm active trong MongoDB...")
    
    success_count = 0
    error_count = 0
    
    for idx, r in enumerate(records):
        doi_tuong_id = r.get("doi_tuong_id")
        ky = r.get("ky_du_lieu")
        if not doi_tuong_id or not ky:
            continue
        try:
            res = await service.thuc_hien_tinh_diem(
                doi_tuong_id=doi_tuong_id,
                ky_du_lieu=ky,
                luu_ket_qua=True,
                nguoi_tinh="cli_script"
            )
            success_count += 1
            if (idx + 1) % 250 == 0 or idx < 5:
                print(f"[{idx+1}/{total_records}] ✅ {doi_tuong_id:15s} (Kỳ {ky:8s}) -> Điểm: {res.tong_diem:.2f} / 5.0 | Xếp hạng: {res.xep_hang}")
        except Exception as e:
            error_count += 1
            print(f"[{idx+1}/{total_records}] ❌ LỖI {doi_tuong_id} (Kỳ {ky}): {e}")
            
    elapsed = time.time() - start_time
    print("============================================================")
    print(f"[*] HOÀN THÀNH TÍNH ĐIỂM TOÀN BỘ DỮ LIỆU IN {elapsed:.2f} GIÂY")
    print(f"    - Tổng bản ghi xử lý : {total_records}")
    print(f"    - Thành công          : {success_count}")
    print(f"    - Thất bại            : {error_count}")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
