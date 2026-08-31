import sys
import asyncio

sys.path.insert(0, ".")

from app.core.database import connect_to_mongo
from app.services.tinh_diem_service import TinhDiemService

async def main():
    try:
        await connect_to_mongo()
    except Exception as e:
        print("Connect mongo error/already connected:", e)
        
    service = TinhDiemService()
    res = await service.thuc_hien_tinh_diem("HSBCVN", "T12/2025", luu_ket_qua=False)
    print(f"tong_diem: {res.tong_diem}, xep_hang: {res.xep_hang}")
    for g in res.ket_qua_cac_nhom:
        print(f"  Nhóm: {g.ma_nhom}, diem_dl: {g.diem_dinh_luong}, diem_dt: {g.diem_dinh_tinh}")
        for c in g.ket_qua_cac_chi_tieu:
            print(f"    ct: {c.ma_chi_tieu_goc}, trang_thai: {c.trang_thai}, dien_giai: {c.dien_giai}, diem_nguong: {c.diem_theo_nguong}")

if __name__ == "__main__":
    asyncio.run(main())
