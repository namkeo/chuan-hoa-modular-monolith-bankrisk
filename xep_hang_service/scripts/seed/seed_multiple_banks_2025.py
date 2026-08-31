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
logger = logging.getLogger(__name__)

async def seed_multiple_banks():
    await connect_to_mongo()
    db = get_database()

    # =========================================================================
    # 1. TẠO CÁC ĐỐI TƯỢNG ĐÁNH GIÁ (5 NGÂN HÀNG HÀNG ĐẦU VIỆT NAM)
    # =========================================================================
    danh_sach_doi_tuong = [
        {
            "_id": "NH_001",
            "ma_doi_tuong": "NH_001",
            "ten_doi_tuong": "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)",
            "ten_viet_tat": "VCB",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "ap_dung_thong_tu_41": True,
            "is_active": 1
        },
        {
            "_id": "NH_002",
            "ma_doi_tuong": "NH_002",
            "ten_doi_tuong": "Ngân hàng TMCP Công thương Việt Nam (VietinBank)",
            "ten_viet_tat": "CTG",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "ap_dung_thong_tu_41": True,
            "is_active": 1
        },
        {
            "_id": "NH_003",
            "ma_doi_tuong": "NH_003",
            "ten_doi_tuong": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam (BIDV)",
            "ten_viet_tat": "BID",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "ap_dung_thong_tu_41": True,
            "is_active": 1
        },
        {
            "_id": "NH_004",
            "ma_doi_tuong": "NH_004",
            "ten_doi_tuong": "Ngân hàng TMCP Quân đội (MBBank)",
            "ten_viet_tat": "MBB",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "ap_dung_thong_tu_41": True,
            "is_active": 1
        },
        {
            "_id": "NH_005",
            "ma_doi_tuong": "NH_005",
            "ten_doi_tuong": "Ngân hàng TMCP Việt Nam Thịnh Vượng (VPBank)",
            "ten_viet_tat": "VPB",
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "ap_dung_thong_tu_41": True,
            "is_active": 1
        }
    ]

    for dt in danh_sach_doi_tuong:
        await db.DoiTuongDanhGia.replace_one({"_id": dt["_id"]}, dt, upsert=True)
    logger.info(f"Đã đăng ký đầy đủ {len(danh_sach_doi_tuong)} Tổ chức tín dụng vào collection 'DoiTuongDanhGia'.")

    # =========================================================================
    # 2. TẠO DỮ LIỆU ĐẦU VÀO ĐỊNH LƯỢNG ĐẦY ĐỦ CÁC BIẾN CỦA 22 CHỈ TIÊU
    # =========================================================================
    du_lieu_tinh_diem_list = [
        # NH_001 (Vietcombank - VCB)
        {
            "_id": "DL_NH001_2025_V1",
            "doi_tuong_id": "NH_001",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True},
            "du_lieu": {
                # Nhóm 1: Vốn
                "C": 14000, "RWA": 100000, "VON_CAP_1": 12000, "KOR": 100, "KMR": 50,
                # Nhóm 2: Chất lượng tài sản
                "NO_XAU": 1100, "NO_XAU_VAMC_CHUA_XU_LY": 0, "NO_CO_TIEM_AN_THANH_NO_XAU": 100, "TONG_NO": 110000,
                "NO_NHOM_2": 1500, "DU_NO_KHACH_HANG_LON": 15000, "DU_NO_TO_CHUC_CA_NHAN": 110000,
                "NO_NGOAI_BANG_3_5": 50, "TONG_NO_NGOAI_BANG_1_5": 120000,
                "DU_NO_THANH_VIEN_QTDND": 0, "TONG_DU_NO_CHO_VAY": 110000,
                "DU_PHONG_CHUNG_KHOAN": 10, "TONG_SO_DU_CHUNG_KHOAN": 5000,
                "DU_NO_BAT_DONG_SAN": 8000, "TONG_DU_NO_TIN_DUNG": 110000,
                # Nhóm 3: Quản trị điều hành
                "CHI_PHI_HOAT_DONG": 2200, "TONG_THU_NHAP_HOAT_DONG": 7000,
                # Nhóm 4: Kết quả kinh doanh
                "LOI_NHUAN_TRUOC_THUE": 4000, "VON_CHU_SO_HUU_BINH_QUAN": 16000,
                "TONG_TAI_SAN_BINH_QUAN": 160000, "THU_NHAP_LAI_THUAN": 5500,
                "TAI_SAN_CO_SINH_LAI_BINH_QUAN": 140000, "LAI_PHAI_THU": 800, "THU_NHAP_TU_LAI": 10000,
                # Nhóm 5: Khả năng thanh khoản
                "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 35000, "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 4500,
                "NGUON_VON_NGAN_HAN": 90000, "DU_NO_CHO_VAY": 110000, "TONG_TIEN_GUI": 120000,
                "TIEN_GUI_KHACH_HANG_LON": 6000,
                # Nhóm 6: Mức độ nhạy cảm RRTT
                "TY_LE_TRANG_THAI_NGOAI_TE": 4.5, "TAI_SAN_NHAY_CAM_LAI_SUAT": 90000,
                "NO_NHAY_CAM_LAI_SUAT": 85000, "VON_CHU_SO_HUU": 16000
            },
            "trang_thai": "DA_PHE_DUYET",
            "is_active": 1
        },

        # NH_002 (VietinBank - CTG)
        {
            "_id": "DL_NH002_2025_V1",
            "doi_tuong_id": "NH_002",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True},
            "du_lieu": {
                "C": 12500, "RWA": 105000, "VON_CAP_1": 10500, "KOR": 120, "KMR": 60,
                "NO_XAU": 1350, "NO_XAU_VAMC_CHUA_XU_LY": 0, "NO_CO_TIEM_AN_THANH_NO_XAU": 150, "TONG_NO": 115000,
                "NO_NHOM_2": 1800, "DU_NO_KHACH_HANG_LON": 18000, "DU_NO_TO_CHUC_CA_NHAN": 115000,
                "NO_NGOAI_BANG_3_5": 80, "TONG_NO_NGOAI_BANG_1_5": 125000,
                "DU_NO_THANH_VIEN_QTDND": 0, "TONG_DU_NO_CHO_VAY": 115000,
                "DU_PHONG_CHUNG_KHOAN": 15, "TONG_SO_DU_CHUNG_KHOAN": 6000,
                "DU_NO_BAT_DONG_SAN": 9500, "TONG_DU_NO_TIN_DUNG": 115000,
                "CHI_PHI_HOAT_DONG": 2400, "TONG_THU_NHAP_HOAT_DONG": 6200,
                "LOI_NHUAN_TRUOC_THUE": 3200, "VON_CHU_SO_HUU_BINH_QUAN": 14500,
                "TONG_TAI_SAN_BINH_QUAN": 155000, "THU_NHAP_LAI_THUAN": 4800,
                "TAI_SAN_CO_SINH_LAI_BINH_QUAN": 135000, "LAI_PHAI_THU": 950, "THU_NHAP_TU_LAI": 9200,
                "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 31000, "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 5200,
                "NGUON_VON_NGAN_HAN": 88000, "DU_NO_CHO_VAY": 115000, "TONG_TIEN_GUI": 118000,
                "TIEN_GUI_KHACH_HANG_LON": 7500,
                "TY_LE_TRANG_THAI_NGOAI_TE": 5.2, "TAI_SAN_NHAY_CAM_LAI_SUAT": 88000,
                "NO_NHAY_CAM_LAI_SUAT": 82000, "VON_CHU_SO_HUU": 14500
            },
            "trang_thai": "DA_PHE_DUYET",
            "is_active": 1
        },

        # NH_003 (BIDV - BID)
        {
            "_id": "DL_NH003_2025_V1",
            "doi_tuong_id": "NH_003",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True},
            "du_lieu": {
                "C": 13000, "RWA": 115000, "VON_CAP_1": 11000, "KOR": 130, "KMR": 70,
                "NO_XAU": 1600, "NO_XAU_VAMC_CHUA_XU_LY": 0, "NO_CO_TIEM_AN_THANH_NO_XAU": 200, "TONG_NO": 125000,
                "NO_NHOM_2": 2100, "DU_NO_KHACH_HANG_LON": 22000, "DU_NO_TO_CHUC_CA_NHAN": 125000,
                "NO_NGOAI_BANG_3_5": 100, "TONG_NO_NGOAI_BANG_1_5": 135000,
                "DU_NO_THANH_VIEN_QTDND": 0, "TONG_DU_NO_CHO_VAY": 125000,
                "DU_PHONG_CHUNG_KHOAN": 20, "TONG_SO_DU_CHUNG_KHOAN": 7000,
                "DU_NO_BAT_DONG_SAN": 11000, "TONG_DU_NO_TIN_DUNG": 125000,
                "CHI_PHI_HOAT_DONG": 2600, "TONG_THU_NHAP_HOAT_DONG": 6500,
                "LOI_NHUAN_TRUOC_THUE": 3100, "VON_CHU_SO_HUU_BINH_QUAN": 15000,
                "TONG_TAI_SAN_BINH_QUAN": 170000, "THU_NHAP_LAI_THUAN": 5100,
                "TAI_SAN_CO_SINH_LAI_BINH_QUAN": 150000, "LAI_PHAI_THU": 1100, "THU_NHAP_TU_LAI": 9800,
                "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 33000, "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 6000,
                "NGUON_VON_NGAN_HAN": 95000, "DU_NO_CHO_VAY": 125000, "TONG_TIEN_GUI": 130000,
                "TIEN_GUI_KHACH_HANG_LON": 9000,
                "TY_LE_TRANG_THAI_NGOAI_TE": 6.0, "TAI_SAN_NHAY_CAM_LAI_SUAT": 92000,
                "NO_NHAY_CAM_LAI_SUAT": 86000, "VON_CHU_SO_HUU": 15000
            },
            "trang_thai": "DA_PHE_DUYET",
            "is_active": 1
        },

        # NH_004 (MBBank - MBB)
        {
            "_id": "DL_NH004_2025_V1",
            "doi_tuong_id": "NH_004",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True},
            "du_lieu": {
                "C": 11000, "RWA": 80000, "VON_CAP_1": 9500, "KOR": 80, "KMR": 40,
                "NO_XAU": 900, "NO_XAU_VAMC_CHUA_XU_LY": 0, "NO_CO_TIEM_AN_THANH_NO_XAU": 80, "TONG_NO": 85000,
                "NO_NHOM_2": 1100, "DU_NO_KHACH_HANG_LON": 11000, "DU_NO_TO_CHUC_CA_NHAN": 85000,
                "NO_NGOAI_BANG_3_5": 30, "TONG_NO_NGOAI_BANG_1_5": 90000,
                "DU_NO_THANH_VIEN_QTDND": 0, "TONG_DU_NO_CHO_VAY": 85000,
                "DU_PHONG_CHUNG_KHOAN": 8, "TONG_SO_DU_CHUNG_KHOAN": 4000,
                "DU_NO_BAT_DONG_SAN": 6500, "TONG_DU_NO_TIN_DUNG": 85000,
                "CHI_PHI_HOAT_DONG": 1800, "TONG_THU_NHAP_HOAT_DONG": 5600,
                "LOI_NHUAN_TRUOC_THUE": 3000, "VON_CHU_SO_HUU_BINH_QUAN": 13000,
                "TONG_TAI_SAN_BINH_QUAN": 110000, "THU_NHAP_LAI_THUAN": 4200,
                "TAI_SAN_CO_SINH_LAI_BINH_QUAN": 95000, "LAI_PHAI_THU": 600, "THU_NHAP_TU_LAI": 8000,
                "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 26000, "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 3200,
                "NGUON_VON_NGAN_HAN": 62000, "DU_NO_CHO_VAY": 85000, "TONG_TIEN_GUI": 90000,
                "TIEN_GUI_KHACH_HANG_LON": 4500,
                "TY_LE_TRANG_THAI_NGOAI_TE": 3.8, "TAI_SAN_NHAY_CAM_LAI_SUAT": 65000,
                "NO_NHAY_CAM_LAI_SUAT": 60000, "VON_CHU_SO_HUU": 13000
            },
            "trang_thai": "DA_PHE_DUYET",
            "is_active": 1
        },

        # NH_005 (VPBank - VPB)
        {
            "_id": "DL_NH005_2025_V1",
            "doi_tuong_id": "NH_005",
            "ky_du_lieu": "2025",
            "phien_ban": 1,
            "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
            "thuoc_tinh": {"ap_dung_thong_tu_41": True},
            "du_lieu": {
                "C": 12000, "RWA": 85000, "VON_CAP_1": 10000, "KOR": 90, "KMR": 45,
                "NO_XAU": 1800, "NO_XAU_VAMC_CHUA_XU_LY": 0, "NO_CO_TIEM_AN_THANH_NO_XAU": 300, "TONG_NO": 90000,
                "NO_NHOM_2": 2400, "DU_NO_KHACH_HANG_LON": 14000, "DU_NO_TO_CHUC_CA_NHAN": 90000,
                "NO_NGOAI_BANG_3_5": 120, "TONG_NO_NGOAI_BANG_1_5": 98000,
                "DU_NO_THANH_VIEN_QTDND": 0, "TONG_DU_NO_CHO_VAY": 90000,
                "DU_PHONG_CHUNG_KHOAN": 25, "TONG_SO_DU_CHUNG_KHOAN": 4500,
                "DU_NO_BAT_DONG_SAN": 12000, "TONG_DU_NO_TIN_DUNG": 90000,
                "CHI_PHI_HOAT_DONG": 2100, "TONG_THU_NHAP_HOAT_DONG": 6000,
                "LOI_NHUAN_TRUOC_THUE": 2600, "VON_CHU_SO_HUU_BINH_QUAN": 14000,
                "TONG_TAI_SAN_BINH_QUAN": 120000, "THU_NHAP_LAI_THUAN": 4600,
                "TAI_SAN_CO_SINH_LAI_BINH_QUAN": 102000, "LAI_PHAI_THU": 1200, "THU_NHAP_TU_LAI": 8500,
                "TAI_SAN_THANH_KHOAN_CAO_BINH_QUAN": 27000, "VON_NGAN_HAN_CHO_VAY_TRUNG_DAI_HAN": 4100,
                "NGUON_VON_NGAN_HAN": 68000, "DU_NO_CHO_VAY": 90000, "TONG_TIEN_GUI": 92000,
                "TIEN_GUI_KHACH_HANG_LON": 5500,
                "TY_LE_TRANG_THAI_NGOAI_TE": 4.2, "TAI_SAN_NHAY_CAM_LAI_SUAT": 70000,
                "NO_NHAY_CAM_LAI_SUAT": 64000, "VON_CHU_SO_HUU": 14000
            },
            "trang_thai": "DA_PHE_DUYET",
            "is_active": 1
        }
    ]

    for dl in du_lieu_tinh_diem_list:
        await db.DuLieuTinhDiem.replace_one({"_id": dl["_id"]}, dl, upsert=True)
    logger.info(f"🎉 Đã nạp đầy đủ dữ liệu định lượng của 22 chỉ tiêu cho 5 Ngân hàng năm 2025.")

    # =========================================================================
    # 3. TẠO DỮ LIỆU SAI PHẠM TRONG DuLieuSaiPham KỲ 2025
    # =========================================================================
    await db.DuLieuSaiPham.delete_many({"ky_du_lieu": "2025"})

    sai_pham_multiple_banks = [
        # NH_001 (Vietcombank): 3 sai phạm nhóm C
        {
            "_id": "SP_NH001_2025_C_a", "doi_tuong_id": "NH_001", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C", "ma_chi_tieu": "C_DT", "ma_hanh_vi_vi_pham": "C_DT.a",
            "noi_dung_chi_tiet": "Chưa bổ sung quy định nội bộ đầy đủ",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": False,
            "phat_hien_4_nam_truoc": True, "da_khac_phuc_song": False, "co_muc_phat_tien": False,
            "so_lan_vi_pham": 1, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_C_b", "doi_tuong_id": "NH_001", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C", "ma_chi_tieu": "C_DT", "ma_hanh_vi_vi_pham": "C_DT.b",
            "noi_dung_chi_tiet": "Vi phạm quy định an toàn vốn (Phạt 150tr, 3 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 150.0, "muc_phat_tien_trung_binh": 150.0,
            "so_lan_vi_pham": 3, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH001_2025_C_c", "doi_tuong_id": "NH_001", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C", "ma_chi_tieu": "C_DT", "ma_hanh_vi_vi_pham": "C_DT.c",
            "noi_dung_chi_tiet": "Vi phạm vốn điều lệ (Phạt 250tr, 5 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 250.0, "muc_phat_tien_trung_binh": 250.0,
            "so_lan_vi_pham": 5, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },

        # NH_002 (VietinBank): 1 sai phạm nhóm M
        {
            "_id": "SP_NH002_2025_M_e", "doi_tuong_id": "NH_002", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "M", "ma_chi_tieu": "M_DT", "ma_hanh_vi_vi_pham": "M_DT.e",
            "noi_dung_chi_tiet": "Vi phạm quy định thông tin báo cáo (Phạt 80tr, 2 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 80.0, "muc_phat_tien_trung_binh": 80.0,
            "so_lan_vi_pham": 2, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },

        # NH_003 (BIDV): 2 sai phạm (nhóm A và M)
        {
            "_id": "SP_NH003_2025_A_d", "doi_tuong_id": "NH_003", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "A", "ma_chi_tieu": "A_DT", "ma_hanh_vi_vi_pham": "A_DT.d",
            "noi_dung_chi_tiet": "Phân loại tài sản có và trích lập dự phòng chưa đúng (Phạt 180tr, 2 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 180.0, "muc_phat_tien_trung_binh": 180.0,
            "so_lan_vi_pham": 2, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH003_2025_M_e", "doi_tuong_id": "NH_003", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "M", "ma_chi_tieu": "M_DT", "ma_hanh_vi_vi_pham": "M_DT.e",
            "noi_dung_chi_tiet": "Chậm gửi báo cáo thống kê (Phạt 90tr, 1 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 90.0, "muc_phat_tien_trung_binh": 90.0,
            "so_lan_vi_pham": 1, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },

        # NH_004 (MBBank): 1 sai phạm nhẹ nhóm C
        {
            "_id": "SP_NH004_2025_C_a", "doi_tuong_id": "NH_004", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "C", "ma_chi_tieu": "C_DT", "ma_hanh_vi_vi_pham": "C_DT.a",
            "noi_dung_chi_tiet": "Chưa hoàn thành rà soát quy định nội bộ (1 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": False, "so_lan_vi_pham": 1, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },

        # NH_005 (VPBank): 2 sai phạm (nhóm A và M)
        {
            "_id": "SP_NH005_2025_A_g", "doi_tuong_id": "NH_005", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "A", "ma_chi_tieu": "A_DT", "ma_hanh_vi_vi_pham": "A_DT.g",
            "noi_dung_chi_tiet": "Vi phạm hạn chế cấp tín dụng (Phạt 220tr, 3 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 220.0, "muc_phat_tien_trung_binh": 220.0,
            "so_lan_vi_pham": 3, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        },
        {
            "_id": "SP_NH005_2025_M_e", "doi_tuong_id": "NH_005", "ky_du_lieu": "2025",
            "ma_nhom_chi_tieu": "M", "ma_chi_tieu": "M_DT", "ma_hanh_vi_vi_pham": "M_DT.e",
            "noi_dung_chi_tiet": "Vi phạm chế độ thông tin báo cáo (Phạt 120tr, 2 lần)",
            "co_quan_quan_ly_phat_hien": True, "phat_hien_trong_nam_xep_hang": True,
            "co_muc_phat_tien": True, "muc_phat_tien_quyet_dinh": 120.0, "muc_phat_tien_trung_binh": 120.0,
            "so_lan_vi_pham": 2, "is_active": 1, "ngay_tao": datetime.now().isoformat()
        }
    ]

    await db.DuLieuSaiPham.insert_many(sai_pham_multiple_banks)
    logger.info(f"🎉 Đã chèn {len(sai_pham_multiple_banks)} bản ghi sai phạm vào collection 'DuLieuSaiPham'.")

    # =========================================================================
    # 4. CHẠY TÍNH ĐIỂM HOÀN CHỈNH VÀ LƯU VÀO KetQuaTinhDiem CHO CẢ 5 NGÂN HÀNG
    # =========================================================================
    service = TinhDiemService()
    ket_qua_list = []

    for dt in danh_sach_doi_tuong:
        doi_tuong_id = dt["_id"]
        res = await service.thuc_hien_tinh_diem(doi_tuong_id, "2025", luu_ket_qua=True)
        ket_qua_list.append(res)
        logger.info(f"--> Đã tính xong {res.doi_tuong['ten_doi_tuong']}: Tổng điểm = {res.tong_diem} | Xếp hạng = {res.xep_hang}")

    # =========================================================================
    # 5. IN BẢNG TỔNG HỢP SO SÁNH ĐIỂM & XẾP HẠNG 5 NGÂN HÀNG KỲ 2025
    # =========================================================================
    print("\n" + "=" * 115)
    print("BẢNG TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ ĐIỂM & XẾP HẠNG TÍN DỤNG KỲ 2025 (THÔNG TƯ 52 / THÔNG TƯ 23)".center(115))
    print("=" * 115)
    print(f"{'Mã NH':<8} | {'Tên Ngân Hàng':<38} | {'C (20%)':<8} | {'A (30%)':<8} | {'M (10%)':<8} | {'E (20%)':<8} | {'L (15%)':<8} | {'S (5%)':<7} | {'Tổng':<5} | {'Hạng'}")
    print("-" * 115)

    for res in ket_qua_list:
        nhom_dict = {nhom.ma_nhom: nhom.diem_nhom for nhom in res.ket_qua_cac_nhom}
        c = nhom_dict.get("C", 0.0)
        a = nhom_dict.get("A", 0.0)
        m = nhom_dict.get("M", 0.0)
        e = nhom_dict.get("E", 0.0)
        l = nhom_dict.get("L", 0.0)
        s = nhom_dict.get("S", 0.0)

        ma_nh = res.doi_tuong["ma_doi_tuong"]
        ten_nh = res.doi_tuong["ten_doi_tuong"]
        if len(ten_nh) > 38:
            ten_nh = ten_nh[:35] + "..."

        print(f"{ma_nh:<8} | {ten_nh:<38} | {c:<8.2f} | {a:<8.2f} | {m:<8.2f} | {e:<8.2f} | {l:<8.2f} | {s:<7.2f} | {res.tong_diem:<5.2f} |  {res.xep_hang}")

    print("=" * 115 + "\n")

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed_multiple_banks())
