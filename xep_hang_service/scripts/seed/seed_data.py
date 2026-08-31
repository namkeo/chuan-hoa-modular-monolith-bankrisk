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
logger = logging.getLogger("seed_data")

async def run_seed():
    logger.info(f"Connecting to MongoDB at {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. Collection BoTieuChi
    bo_tieu_chi_data = {
        "_id": "BTC_2026_V1",
        "ma_bo_tieu_chi": "BTC_2026",
        "ten_bo_tieu_chi": "Bộ tiêu chí đánh giá rủi ro tổ chức tín dụng",
        "phien_ban": 1,
        "tu_ngay": "2026-01-01",
        "den_ngay": None,
        "trang_thai": "DANG_AP_DUNG",
        "mo_ta": "Bộ tiêu chí áp dụng đánh giá xếp hạng năm 2026",
        "can_cu_phap_ly": [
            {"ma_van_ban": "TT52", "ten_van_ban": "Thông tư số 52"},
            {"ma_van_ban": "TT23", "ten_van_ban": "Thông tư số 23 sửa đổi, bổ sung"}
        ],
        "ngay_tao": "2026-07-27T10:00:00",
        "nguoi_tao": "admin",
        "is_active": 1
    }
    await db.BoTieuChi.replace_one({"_id": "BTC_2026_V1"}, bo_tieu_chi_data, upsert=True)
    logger.info("Seeded BoTieuChi: BTC_2026_V1")

    # 2. Collection NhomTieuChi
    nhom_c = {
        "_id": "NTC_C",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "C",
        "so_thu_tu": 1,
        "ten_nhom": "VỐN",
        "trong_so_tieu_chi": 20,
        "trong_so_nhom_dinh_luong": 15,
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }
    nhom_a = {
        "_id": "NTC_A",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "ma_nhom": "A",
        "so_thu_tu": 2,
        "ten_nhom": "CHẤT LƯỢNG TÀI SẢN",
        "trong_so_tieu_chi": 30,
        "trong_so_nhom_dinh_luong": 25,
        "thu_tu_hien_thi": 2,
        "ghi_chu": "Trọng số tiêu chí 30%, trọng số nhóm định lượng 25%",
        "is_active": 1
    }
    await db.NhomTieuChi.replace_one({"_id": "NTC_C"}, nhom_c, upsert=True)
    await db.NhomTieuChi.replace_one({"_id": "NTC_A"}, nhom_a, upsert=True)
    logger.info("Seeded NhomTieuChi: NTC_C, NTC_A")

    # 3. Collection ChiTieu
    # Chỉ tiêu 1.1 (Không áp dụng TT41)
    ct_1_1 = {
        "_id": "CT_1_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "1.1",
        "ma_chi_tieu_goc": "1.1",
        "ten_chi_tieu": "Tỷ lệ an toàn vốn không thực hiện theo Thông tư 41",
        "mo_ta_cong_thuc": "Vốn tự có / Tổng tài sản Có rủi ro × 100%",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "VON_TU_CO"},
                        {"ma_bien": "TONG_TAI_SAN_CO_RUI_RO"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "VON_TU_CO", "ten_bien": "Vốn tự có", "bat_buoc": True},
            {"ma_bien": "TONG_TAI_SAN_CO_RUI_RO", "ten_bien": "Tổng tài sản Có rủi ro", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {
            "kieu": "SO_SANH",
            "truong": "ap_dung_thong_tu_41",
            "phep_so_sanh": "BANG",
            "gia_tri": False
        },
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 100,
                "cac_muc_diem": [
                    {"thu_tu": 1, "diem": 5, "tu": 12, "bao_gom_tu": True, "den": None, "bao_gom_den": False},
                    {"thu_tu": 2, "diem": 4, "tu": 10, "bao_gom_tu": True, "den": 12, "bao_gom_den": False},
                    {"thu_tu": 3, "diem": 3, "tu": 9, "bao_gom_tu": True, "den": 10, "bao_gom_den": False},
                    {"thu_tu": 4, "diem": 2, "tu": 8, "bao_gom_tu": True, "den": 9, "bao_gom_den": False},
                    {"thu_tu": 5, "diem": 1, "tu": None, "bao_gom_tu": False, "den": 8, "bao_gom_den": False}
                ]
            }
        ],
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # Chỉ tiêu 1.1.a (Thực hiện theo TT41)
    ct_1_1_a = {
        "_id": "CT_1_1_A",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "1.1.a",
        "ma_chi_tieu_goc": "1.1",
        "ten_chi_tieu": "Tỷ lệ an toàn vốn thực hiện theo Thông tư 41",
        "mo_ta_cong_thuc": "C / [RWA + 12,5 × (KOR + KMR)] × 100%",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "C"},
                        {
                            "phep_toan": "CONG",
                            "tham_so": [
                                {"ma_bien": "RWA"},
                                {
                                    "phep_toan": "NHAN",
                                    "tham_so": [
                                        {"gia_tri": 12.5},
                                        {
                                            "phep_toan": "CONG",
                                            "tham_so": [
                                                {"ma_bien": "KOR"},
                                                {"ma_bien": "KMR"}
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "C", "ten_bien": "Vốn tự có", "bat_buoc": True},
            {"ma_bien": "RWA", "ten_bien": "Tài sản Có rủi ro tín dụng", "bat_buoc": True},
            {"ma_bien": "KOR", "ten_bien": "Vốn yêu cầu rủi ro hoạt động", "bat_buoc": True},
            {"ma_bien": "KMR", "ten_bien": "Vốn yêu cầu rủi ro thị trường", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {
            "kieu": "SO_SANH",
            "truong": "ap_dung_thong_tu_41",
            "phep_so_sanh": "BANG",
            "gia_tri": True
        },
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 100,
                "cac_muc_diem": [
                    {"thu_tu": 1, "diem": 5, "tu": 12, "bao_gom_tu": True, "den": None, "bao_gom_den": False},
                    {"thu_tu": 2, "diem": 4, "tu": 10, "bao_gom_tu": True, "den": 12, "bao_gom_den": False},
                    {"thu_tu": 3, "diem": 3, "tu": 9, "bao_gom_tu": True, "den": 10, "bao_gom_den": False},
                    {"thu_tu": 4, "diem": 2, "tu": 8, "bao_gom_tu": True, "den": 9, "bao_gom_den": False},
                    {"thu_tu": 5, "diem": 1, "tu": None, "bao_gom_tu": False, "den": 8, "bao_gom_den": False}
                ]
            }
        ],
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # Chỉ tiêu 2.1 (Tỷ lệ nợ xấu)
    ct_2_1 = {
        "_id": "CT_2_1",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.1",
        "ma_chi_tieu_goc": "2.1",
        "ten_chi_tieu": "Tỷ lệ nợ xấu",
        "mo_ta_cong_thuc": "Nợ xấu / Tổng nợ × 100%",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "NO_XAU"},
                        {"ma_bien": "TONG_NO"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "NO_XAU", "ten_bien": "Nợ xấu", "bat_buoc": True},
            {"ma_bien": "TONG_NO", "ten_bien": "Tổng nợ", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 40,
                "cac_muc_diem": [
                    {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": 2, "bao_gom_den": True},
                    {"thu_tu": 2, "diem": 4, "tu": 2, "bao_gom_tu": False, "den": 3, "bao_gom_den": True},
                    {"thu_tu": 3, "diem": 3, "tu": 3, "bao_gom_tu": False, "den": 5, "bao_gom_den": True},
                    {"thu_tu": 4, "diem": 2, "tu": 5, "bao_gom_tu": False, "den": 7, "bao_gom_den": True},
                    {"thu_tu": 5, "diem": 1, "tu": 7, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
                ]
            },
            {
                "ma_loai_doi_tuong": "CONG_TY_TAI_CHINH",
                "ten_loai_doi_tuong": "Công ty tài chính",
                "trong_so": 50,
                "cac_muc_diem": [
                    {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": 2, "bao_gom_den": True},
                    {"thu_tu": 2, "diem": 4, "tu": 2, "bao_gom_tu": False, "den": 4, "bao_gom_den": True},
                    {"thu_tu": 3, "diem": 3, "tu": 4, "bao_gom_tu": False, "den": 6, "bao_gom_den": True},
                    {"thu_tu": 4, "diem": 2, "tu": 6, "bao_gom_tu": False, "den": 8, "bao_gom_den": True},
                    {"thu_tu": 5, "diem": 1, "tu": 8, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
                ]
            }
        ],
        "thu_tu_hien_thi": 1,
        "is_active": 1
    }

    # Chỉ tiêu 2.2 (Tỷ lệ nợ Nhóm 2)
    ct_2_2 = {
        "_id": "CT_2_2",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "2.2",
        "ma_chi_tieu_goc": "2.2",
        "ten_chi_tieu": "Tỷ lệ nợ Nhóm 2 so với tổng nợ",
        "mo_ta_cong_thuc": "Nợ nhóm 2 / Tổng nợ × 100%",
        "cong_thuc": {
            "phep_toan": "NHAN",
            "tham_so": [
                {
                    "phep_toan": "CHIA",
                    "tham_so": [
                        {"ma_bien": "NO_NHOM_2"},
                        {"ma_bien": "TONG_NO"}
                    ]
                },
                {"gia_tri": 100}
            ]
        },
        "danh_sach_bien": [
            {"ma_bien": "NO_NHOM_2", "ten_bien": "Nợ nhóm 2", "bat_buoc": True},
            {"ma_bien": "TONG_NO", "ten_bien": "Tổng nợ", "bat_buoc": True}
        ],
        "don_vi_tinh": "%",
        "loai_chi_tieu": "DINH_LUONG",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {
                "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
                "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
                "trong_so": 60,
                "cac_muc_diem": [
                    {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": 2.5, "bao_gom_den": True},
                    {"thu_tu": 2, "diem": 4, "tu": 2.5, "bao_gom_tu": False, "den": 4, "bao_gom_den": True},
                    {"thu_tu": 3, "diem": 3, "tu": 4, "bao_gom_tu": False, "den": 5.5, "bao_gom_den": True},
                    {"thu_tu": 4, "diem": 2, "tu": 5.5, "bao_gom_tu": False, "den": 7, "bao_gom_den": True},
                    {"thu_tu": 5, "diem": 1, "tu": 7, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
                ]
            }
        ],
        "thu_tu_hien_thi": 2,
        "is_active": 1
    }

    await db.ChiTieu.replace_one({"_id": "CT_1_1"}, ct_1_1, upsert=True)
    await db.ChiTieu.replace_one({"_id": "CT_1_1_A"}, ct_1_1_a, upsert=True)
    await db.ChiTieu.replace_one({"_id": "CT_2_1"}, ct_2_1, upsert=True)
    await db.ChiTieu.replace_one({"_id": "CT_2_2"}, ct_2_2, upsert=True)
    logger.info("Seeded ChiTieu: CT_1_1, CT_1_1_A, CT_2_1, CT_2_2")

    # 4. Collection DoiTuongDanhGia
    doi_tuong = {
        "_id": "NH_001",
        "ma_doi_tuong": "NH_001",
        "ten_doi_tuong": "Ngân hàng A",
        "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
        "ten_loai_doi_tuong": "Ngân hàng thương mại có quy mô lớn",
        "thuoc_tinh": {
            "ap_dung_thong_tu_41": True,
            "quy_mo": "LON",
            "la_chi_nhanh_ngan_hang_nuoc_ngoai": False
        },
        "is_active": 1
    }
    await db.DoiTuongDanhGia.replace_one({"_id": "NH_001"}, doi_tuong, upsert=True)
    logger.info("Seeded DoiTuongDanhGia: NH_001")

    # 5. Collection DuLieuTinhDiem
    du_lieu_tinh_diem = {
        "_id": "DL_NH001_2025_V1",
        "doi_tuong_id": "NH_001",
        "ky_du_lieu": "2025",
        "phien_ban": 1,
        "ma_loai_doi_tuong": "NHTM_QUY_MO_LON",
        "thuoc_tinh": {
            "ap_dung_thong_tu_41": True,
            "quy_mo": "LON"
        },
        "du_lieu": {
            "C": 10000,
            "RWA": 90000,
            "KOR": 100,
            "KMR": 50,
            "VON_CAP_1": 8500,
            "NO_XAU": 900,
            "NO_XAU_VAMC_CHUA_XU_LY": 100,
            "NO_CO_TIEM_AN_THANH_NO_XAU": 120,
            "TONG_NO": 40000,
            "NO_NHOM_2": 1280,
            "DU_NO_KHACH_HANG_LON": 10000,
            "DU_NO_TO_CHUC_CA_NHAN": 50000
        },
        "trang_thai": "DA_PHE_DUYET",
        "nguoi_nhap": "user01",
        "ngay_nhap": "2026-07-27T08:00:00",
        "nguoi_phe_duyet": "user02",
        "ngay_phe_duyet": "2026-07-27T09:00:00",
        "is_active": 1
    }
    await db.DuLieuTinhDiem.replace_one({"_id": "DL_NH001_2025_V1"}, du_lieu_tinh_diem, upsert=True)
    logger.info("Seeded DuLieuTinhDiem: DL_NH001_2025_V1")

    logger.info("Seed data completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_seed())
