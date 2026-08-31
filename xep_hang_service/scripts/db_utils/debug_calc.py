import asyncio
import logging
import sys
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import connect_to_mongo, close_mongo_connection
from app.services.tinh_diem_service import TinhDiemService

async def debug_calc():
    await connect_to_mongo()
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("NH_001", "2025", luu_ket_qua=False)
    
    print("\n================ CHI TIẾT TÍNH ĐIỂM CHO NH_001 ================")
    print(f"Tổng điểm: {res.tong_diem} | Xếp hạng: {res.xep_hang}")
    for nhom in res.ket_qua_cac_nhom:
        print(f"\n📌 Nhóm {nhom.ma_nhom} (Trọng số nhóm: {nhom.trong_so_tieu_chi}%, DL: {nhom.trong_so_nhom_dinh_luong}%, DT: {nhom.trong_so_nhom_dinh_tinh}%):")
        print(f"   - Điểm ĐL: {nhom.diem_dinh_luong} | Điểm ĐT: {nhom.diem_dinh_tinh} | Điểm đóng góp nhóm: {nhom.diem_nhom}")
        for ct in nhom.ket_qua_cac_chi_tieu:
            print(f"     + [{ct.ma_chi_tieu_duoc_chon}] {ct.ten_chi_tieu}: Điểm theo ngưỡng = {ct.diem_theo_nguong}, Trọng số = {ct.trong_so}%, Quy đổi = {ct.diem_quy_doi}")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(debug_calc())
