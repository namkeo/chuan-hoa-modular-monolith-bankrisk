import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

BE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.tinh_diem_service import TinhDiemService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_31_banks")

# Danh sách 31 TCTD / Ngân hàng chuẩn hóa từ file DS_TCTD.xlsx
BANKS_31 = [
    {"_id": "NH_001", "ma_doi_tuong": "NH_001", "ten_doi_tuong": "Ngân hàng TMCP Công thương Việt Nam", "ten_viet_tat": "VietinBank (CTG)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_002", "ma_doi_tuong": "NH_002", "ten_doi_tuong": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "ten_viet_tat": "BIDV (BID)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_003", "ma_doi_tuong": "NH_003", "ten_doi_tuong": "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", "ten_viet_tat": "Agribank (AGR)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": False, "is_active": 1},
    {"_id": "NH_004", "ma_doi_tuong": "NH_004", "ten_doi_tuong": "Ngân hàng TMCP Ngoại thương Việt Nam", "ten_viet_tat": "Vietcombank (VCB)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_005", "ma_doi_tuong": "NH_005", "ten_doi_tuong": "Ngân hàng TMCP Á Châu", "ten_viet_tat": "ACB", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_006", "ma_doi_tuong": "NH_006", "ten_doi_tuong": "Ngân hàng TMCP Lộc Phát Việt Nam", "ten_viet_tat": "LPBank (LPB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_007", "ma_doi_tuong": "NH_007", "ten_doi_tuong": "Ngân hàng TMCP Kỹ Thương Việt Nam", "ten_viet_tat": "Techcombank (TCB)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_008", "ma_doi_tuong": "NH_008", "ten_doi_tuong": "Ngân hàng TMCP Phát triển TP.HCM", "ten_viet_tat": "HDBank (HDB)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_009", "ma_doi_tuong": "NH_009", "ten_doi_tuong": "Ngân hàng TMCP Quân Đội", "ten_viet_tat": "MBBank (MBB)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_010", "ma_doi_tuong": "NH_010", "ten_doi_tuong": "Ngân hàng TMCP Quốc tế Việt Nam", "ten_viet_tat": "VIB", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_011", "ma_doi_tuong": "NH_011", "ten_doi_tuong": "Ngân hàng TMCP Sài Gòn - Hà Nội", "ten_viet_tat": "SHB", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_012", "ma_doi_tuong": "NH_012", "ten_doi_tuong": "Ngân hàng TMCP Tiên Phong", "ten_viet_tat": "TPBank (TPB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_013", "ma_doi_tuong": "NH_013", "ten_doi_tuong": "Ngân hàng TMCP Việt Nam Thịnh Vượng", "ten_viet_tat": "VPBank (VPB)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_014", "ma_doi_tuong": "NH_014", "ten_doi_tuong": "Ngân hàng TMCP Bắc Á", "ten_viet_tat": "Bac A Bank (BAB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_015", "ma_doi_tuong": "NH_015", "ten_doi_tuong": "Ngân hàng TMCP Hàng Hải Việt Nam", "ten_viet_tat": "MSB", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_016", "ma_doi_tuong": "NH_016", "ten_doi_tuong": "Ngân hàng TMCP Việt Á", "ten_viet_tat": "VietABank (VAB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_017", "ma_doi_tuong": "NH_017", "ten_doi_tuong": "Ngân hàng TMCP Đông Nam Á", "ten_viet_tat": "SeABank (SSB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_018", "ma_doi_tuong": "NH_018", "ten_doi_tuong": "Ngân hàng TMCP Bản Việt", "ten_viet_tat": "BVBank (BVB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_019", "ma_doi_tuong": "NH_019", "ten_doi_tuong": "Ngân hàng TMCP Xuất nhập khẩu Việt Nam", "ten_viet_tat": "Eximbank (EIB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_020", "ma_doi_tuong": "NH_020", "ten_doi_tuong": "Ngân hàng TMCP Quốc Dân", "ten_viet_tat": "NCB (NVB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": False, "is_active": 1},
    {"_id": "NH_021", "ma_doi_tuong": "NH_021", "ten_doi_tuong": "Ngân hàng TMCP Nam Á", "ten_viet_tat": "Nam A Bank (NAB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_022", "ma_doi_tuong": "NH_022", "ten_doi_tuong": "Ngân hàng TMCP Phương Đông", "ten_viet_tat": "OCB", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_023", "ma_doi_tuong": "NH_023", "ten_doi_tuong": "Ngân hàng TMCP Bảo Việt", "ten_viet_tat": "BaoVietBank (BVB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": False, "is_active": 1},
    {"_id": "NH_024", "ma_doi_tuong": "NH_024", "ten_doi_tuong": "Ngân hàng TMCP Thịnh Vượng và Phát triển", "ten_viet_tat": "PGBank (PGB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_025", "ma_doi_tuong": "NH_025", "ten_doi_tuong": "Ngân hàng TMCP Sài Gòn Công thương", "ten_viet_tat": "SaigonBank (SGB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_026", "ma_doi_tuong": "NH_026", "ten_doi_tuong": "Ngân hàng TMCP An Bình", "ten_viet_tat": "ABBank (ABB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_027", "ma_doi_tuong": "NH_027", "ten_doi_tuong": "Ngân hàng TMCP Việt Nam Thương Tín", "ten_viet_tat": "Vietbank (VBB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_028", "ma_doi_tuong": "NH_028", "ten_doi_tuong": "Ngân hàng TMCP Kiên Long", "ten_viet_tat": "KienlongBank (KLB)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_029", "ma_doi_tuong": "NH_029", "ten_doi_tuong": "Ngân hàng TMCP Sài Gòn Thương Tín", "ten_viet_tat": "Sacombank (STB)", "ma_loai_doi_tuong": "NHTM_QUY_MO_LON", "ap_dung_thong_tu_41": True, "is_active": 1},
    {"_id": "NH_030", "ma_doi_tuong": "NH_030", "ten_doi_tuong": "Ngân hàng TMCP Đại Chúng Việt Nam", "ten_viet_tat": "PVcomBank (PVC)", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": False, "is_active": 1},
    {"_id": "NH_031", "ma_doi_tuong": "NH_031", "ten_doi_tuong": "Ngân hàng TMCP Sài Gòn", "ten_viet_tat": "SCB", "ma_loai_doi_tuong": "NHTM_VUA_VA_NHO", "ap_dung_thong_tu_41": False, "is_active": 1}
]

def generate_financial_variables(bank_info, idx):
    is_big = bank_info["ma_loai_doi_tuong"] == "NHTM_QUY_MO_LON"
    factor = 1.0 if is_big else 0.45
    
    von_tu_co = round((45000 + idx * 3500) * factor, 2)
    tong_ts_co_rui_ro = round((350000 + idx * 25000) * factor, 2)
    von_cap_1 = round(von_tu_co * 0.88, 2)
    
    tong_du_no = round((300000 + idx * 22000) * factor, 2)
    no_xau = round(tong_du_no * (0.012 + (idx % 4) * 0.003), 2)
    no_nhom_2_den_5 = round(tong_du_no * (0.025 + (idx % 3) * 0.004), 2)
    truc_lap_du_phong = round(no_xau * (1.1 + (idx % 5) * 0.15), 2)
    
    loi_nhuan_sau_thue = round((6500 + idx * 800) * factor, 2)
    tong_tai_san = round((480000 + idx * 35000) * factor, 2)
    von_chu_so_huu = round(von_tu_co * 0.95, 2)
    
    thu_nhap_lai_thuan = round((13000 + idx * 1200) * factor, 2)
    thu_nhap_ngoai_lai = round((3200 + idx * 400) * factor, 2)
    tong_thu_nhap_hd = thu_nhap_lai_thuan + thu_nhap_ngoai_lai
    chi_phi_hoat_dong = round(tong_thu_nhap_hd * (0.32 + (idx % 5) * 0.02), 2)
    
    tien_gui_khach_hang = round(tong_du_no * 1.12, 2)
    von_ngan_han = round(tien_gui_khach_hang * 0.65, 2)
    cho_vay_trung_dai_han = round(tong_du_no * 0.45, 2)
    tai_san_co_thanh_khoan = round(tong_tai_san * 0.18, 2)
    no_ngan_han = round(tong_tai_san * 0.14, 2)
    
    return {
        "VON_TU_CO": von_tu_co,
        "TONG_TAI_SAN_CO_RUI_RO": tong_ts_co_rui_ro,
        "VON_CAP_1": von_cap_1,
        "VON_TU_CO_TT41": von_tu_co * 1.02,
        "TONG_TAI_SAN_CO_RUI_RO_TT41": tong_ts_co_rui_ro * 0.98,
        "VON_CAP_1_TT41": von_cap_1 * 1.01,
        "NO_XAU": no_xau,
        "TONG_DU_NO": tong_du_no,
        "NO_NHOM_2_DEN_5": no_nhom_2_den_5,
        "DU_PHONG_RUI_RO": truc_lap_du_phong,
        "TAI_SAN_TON_DONG": round(tong_tai_san * 0.005, 2),
        "TONG_TAI_SAN": tong_tai_san,
        "CHI_PHI_HOAT_DONG": chi_phi_hoat_dong,
        "TONG_THU_NHAP_HOAT_DONG": tong_thu_nhap_hd,
        "LOI_NHUAN_SAU_THUE": loi_nhuan_sau_thue,
        "VON_CHU_SO_HUU": von_chu_so_huu,
        "THU_NHAP_LAI_THUAN": thu_nhap_lai_thuan,
        "THU_NHAP_NGOAI_LAI": thu_nhap_ngoai_lai,
        "TIEN_GUI_KHACH_HANG": tien_gui_khach_hang,
        "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": round(cho_vay_trung_dai_han * 0.6, 2),
        "NGUON_VON_NGAN_HAN": von_ngan_han,
        "TAI_SAN_CO_THANH_KHOAN": tai_san_co_thanh_khoan,
        "NO_NGAN_HAN_PHAI_TRA": no_ngan_han,
        "TRANG_THAI_NGOAI_TE_NET": round(von_tu_co * 0.04, 2),
        "DO_LECH_NHAY_CAM_LAI_SUAT_GAP": round(von_tu_co * 0.08, 2)
    }

async def seed_all_31_banks():
    logger.info("Connecting to MongoDB...")
    await connect_to_mongo()
    db = get_database()

    # 1. Nạp danh sách 31 Ngân hàng vào collection DoiTuongDanhGia
    for b in BANKS_31:
        await db.DoiTuongDanhGia.replace_one({"_id": b["_id"]}, b, upsert=True)
    logger.info(f"🎉 Đã nạp thành công {len(BANKS_31)} Ngân hàng vào collection 'DoiTuongDanhGia'!")

    # 2. Nạp dữ liệu chỉ tiêu định lượng DuLieuTinhDiem cho 31 Ngân hàng kỳ 2025
    service = TinhDiemService()
    tieu_chi_id = "BTC_2026_V1"
    
    for idx, b in enumerate(BANKS_31):
        dt_id = b["_id"]
        vars_dict = generate_financial_variables(b, idx)
        
        dl_doc = {
            "_id": f"DL_{dt_id}_2025_V1",
            "bo_tieu_chi_id": tieu_chi_id,
            "doi_tuong_id": dt_id,
            "ma_doi_tuong": dt_id,
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ngay_lap": "2025-12-31",
            "nguoi_nhap": "system_seed_31_banks",
            "trang_thai": "DA_DUYET",
            "danh_sach_bien": vars_dict,
            "is_active": 1,
            "ngay_tao": datetime.now().isoformat()
        }
        await db.DuLieuTinhDiem.replace_one({"_id": dl_doc["_id"]}, dl_doc, upsert=True)
        
        # 3. Thực hiện tính điểm và lưu kết quả cho từng ngân hàng
        try:
            res = await service.thuc_hien_tinh_diem(
                doi_tuong_id=dt_id,
                ky_du_lieu="2025",
                luu_ket_qua=True,
                nguoi_tinh="system_seed_31_banks"
            )
            logger.info(f" [{idx+1}/{len(BANKS_31)}] ✅ {b['ten_viet_tat']:25s} | Điểm: {res.tong_diem:.2f} / 5.0 | Xếp hạng: {res.xep_hang}")
        except Exception as e:
            logger.error(f" [{idx+1}/{len(BANKS_31)}] ❌ Lỗi tính điểm {b['ten_viet_tat']}: {e}")

    await close_mongo_connection()
    logger.info("🎉 HOÀN THÀNH KHỞI TẠO VÀ TÍNH ĐIỂM TOÀN BỘ 31 NGÂN HÀNG TRONG MONGODB!")

if __name__ == "__main__":
    asyncio.run(seed_all_31_banks())
