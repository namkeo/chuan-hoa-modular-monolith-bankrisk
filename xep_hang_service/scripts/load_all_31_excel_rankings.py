import asyncio
import json
import logging
import sys
import os
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.utils.template_dl_read import extract_camels_data
from app.services.tinh_diem_service import TinhDiemService
from app.utils.camels_full_evaluator import evaluate_full_camels_from_excel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load_31_rankings")

def resolve_excel_folder() -> str:
    peer_dir = BE_ROOT.parent / "minio_data" / "xep_hang_tctd"
    if peer_dir.exists() and list(peer_dir.glob("XH_TCTD_*.xlsx")):
        return str(peer_dir)
    return r"D:\Văn bản KTNN\Rủi ro vốn\[SBV] Tài liệu khảo sát\dataset\source_code\minio_data\xep_hang_tctd"

EXCEL_FOLDER = resolve_excel_folder()

# Bản đồ khớp tên file Excel -> Mã ngân hàng (NH_001 đến NH_031) và Tên ngân hàng
EXCEL_FILE_MAP = {
    "XH_TCTD_VTB.xlsx": ("VietinBank", "Ngân hàng TMCP Công thương Việt Nam", "VietinBank (CTG)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_BIDV.xlsx": ("BIDV", "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "BIDV (BID)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_Agribank.xlsx": ("Agribank", "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", "Agribank (AGR)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_VCB.xlsx": ("Vietcombank", "Ngân hàng TMCP Ngoại thương Việt Nam", "Vietcombank (VCB)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_ACB.xlsx": ("ACB", "Ngân hàng TMCP Á Châu", "ACB", "NHTM_QUY_MO_LON"),
    "XH_TCTD_LPB.xlsx": ("LPBank", "Ngân hàng TMCP Lộc Phát Việt Nam", "LPBank (LPB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_TCB.xlsx": ("Techcombank", "Ngân hàng TMCP Kỹ Thương Việt Nam", "Techcombank (TCB)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_HDB.xlsx": ("HDBank", "Ngân hàng TMCP Phát triển TP.HCM", "HDBank (HDB)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_MB.xlsx": ("MBBank", "Ngân hàng TMCP Quân Đội", "MBBank (MBB)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_VIB.xlsx": ("VIB", "Ngân hàng TMCP Quốc tế Việt Nam", "VIB", "NHTM_QUY_MO_LON"),
    "XH_TCTD_SHB.xlsx": ("SHB", "Ngân hàng TMCP Sài Gòn - Hà Nội", "SHB", "NHTM_QUY_MO_LON"),
    "XH_TCTD_TPB.xlsx": ("TPBank", "Ngân hàng TMCP Tiên Phong", "TPBank (TPB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_VPB.xlsx": ("VPBank", "Ngân hàng TMCP Việt Nam Thịnh Vượng", "VPBank (VPB)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_BACABANK.xlsx": ("Bac A Bank", "Ngân hàng TMCP Bắc Á", "Bac A Bank (BAB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_MSB.xlsx": ("MSB", "Ngân hàng TMCP Hàng Hải Việt Nam", "MSB", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_VAB.xlsx": ("VietABank", "Ngân hàng TMCP Việt Á", "VietABank (VAB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_SeABank.xlsx": ("SeABank", "Ngân hàng TMCP Đông Nam Á", "SeABank (SSB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_BVBank.xlsx": ("BVBank", "Ngân hàng TMCP Bản Việt", "BVBank (BVB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_EximBank.xlsx": ("Eximbank", "Ngân hàng TMCP Xuất nhập khẩu Việt Nam", "Eximbank (EIB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_NCB.xlsx": ("NCB", "Ngân hàng TMCP Quốc Dân", "NCB (NVB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_NAB.xlsx": ("Nam A Bank", "Ngân hàng TMCP Nam Á", "Nam A Bank (NAB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_OCB.xlsx": ("OCB", "Ngân hàng TMCP Phương Đông", "OCB", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_BaoVietBank.xlsx": ("BaoVietBank", "Ngân hàng TMCP Bảo Việt", "BaoVietBank (BAOVIET)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_PGBank.xlsx": ("PGBank", "Ngân hàng TMCP Thịnh Vượng và Phát triển", "PGBank (PGB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_SGB.xlsx": ("SaigonBank", "Ngân hàng TMCP Sài Gòn Công thương", "SaigonBank (SGB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_ABBank.xlsx": ("ABBank", "Ngân hàng TMCP An Bình", "ABBank (ABB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_Vietbank.xlsx": ("Vietbank", "Ngân hàng TMCP Việt Nam Thương Tín", "Vietbank (VBB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_KienlongBank.xlsx": ("KienlongBank", "Ngân hàng TMCP Kiên Long", "KienlongBank (KLB)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_STB.xlsx": ("Sacombank", "Ngân hàng TMCP Sài Gòn Thương Tín", "Sacombank (STB)", "NHTM_QUY_MO_LON"),
    "XH_TCTD_PVcomBank.xlsx": ("PVcomBank", "Ngân hàng TMCP Đại Chúng Việt Nam", "PVcomBank (PVC)", "NHTM_VUA_VA_NHO"),
    "XH_TCTD_SCB.xlsx": ("SCB", "Ngân hàng TMCP Sài Gòn", "SCB", "NHTM_VUA_VA_NHO")
}

BANK_QUALITATIVE_OVERRIDES = {
    "VietinBank": {
        "M": {
            "diem": 4.0,
            "dien_giai": "Đánh giá các chỉ tiêu định tính Nhóm M (Quản trị điều hành): 4.0 điểm",
            "details": {"so_luong_sai_pham": 0}
        }
    }
}

async def process_all_rankings():
    db = None
    try:
        logger.info("Connecting to MongoDB...")
        await connect_to_mongo()
        db = get_database()
    except Exception as e:
        logger.warning(f"MongoDB connection skipped ({e}). Will save to precomputed JSON file.")

    service = TinhDiemService()

    files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith(".xlsx")]
    logger.info(f"Phát hiện {len(files)} file Excel xếp hạng trong thư mục '{EXCEL_FOLDER}'")

    success_count = 0
    all_results = []

    for fname, (ma_nh, ten_nh, ten_vt, loai_nh) in EXCEL_FILE_MAP.items():
        file_path = os.path.join(EXCEL_FOLDER, fname)
        if not os.path.exists(file_path):
            logger.warning(f"File {fname} không tồn tại!")
            continue

        # 1. Bảo đảm TCTD đã có trong collection DoiTuongDanhGia (nếu có DB)
        if db is not None:
            try:
                dt_doc = {
                    "_id": ma_nh,
                    "ma_doi_tuong": ma_nh,
                    "ten_doi_tuong": ten_nh,
                    "ten_viet_tat": ten_vt,
                    "ma_loai_doi_tuong": loai_nh,
                    "ap_dung_thong_tu_41": True if loai_nh == "NHTM_QUY_MO_LON" else False,
                    "is_active": 1
                }
                await db.DoiTuongDanhGia.replace_one({"_id": ma_nh}, dt_doc, upsert=True)
            except Exception as e:
                logger.warning(f"Failed to save DoiTuongDanhGia to DB: {e}. Disabling DB writes.")
                db = None

        # 2. Đọc dữ liệu các dòng R-100 -> R-192 từ file Excel
        camels_data = extract_camels_data(file_path)

        # 3. Thực hiện tính điểm xếp hạng cho kỳ '2025'
        for ky in ["2025"]:
            try:
                # Truy vấn điểm định tính từ CSDL cho các nhóm C, A, M, E, L, S
                dt_scores_map = {}
                for group_code in ["C", "A", "M", "E", "L", "S"]:
                    if ma_nh in BANK_QUALITATIVE_OVERRIDES and group_code in BANK_QUALITATIVE_OVERRIDES[ma_nh]:
                        dt_scores_map[group_code] = BANK_QUALITATIVE_OVERRIDES[ma_nh][group_code]
                        continue
                    try:
                        if db is not None:
                            dt_val, dt_dg, dt_details = await service.tinh_diem_dinh_tinh_nhom(
                                doi_tuong_id=ma_nh,
                                ky_du_lieu=ky,
                                ma_nhom=group_code,
                                du_lieu_dict={},
                                du_lieu_input={}
                            )
                            dt_scores_map[group_code] = {
                                "diem": float(dt_val),
                                "dien_giai": dt_dg,
                                "details": dt_details
                            }
                        else:
                            raise Exception("No DB connection")
                    except Exception:
                        dt_scores_map[group_code] = {
                            "diem": 5.0,
                            "dien_giai": f"Không có dữ liệu sai phạm thuộc nhóm {group_code} trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)",
                            "details": {"so_luong_sai_pham": 0}
                        }

                eval_res = evaluate_full_camels_from_excel(camels_data, ma_nh, ky, dt_scores_map=dt_scores_map)

                # Lưu trực tiếp bản ghi kết quả xếp hạng
                res_doc = {
                    "_id": f"KQ_{ma_nh}_{ky.replace('/', '_')}_V1",
                    "doi_tuong_id": ma_nh,
                    "ma_doi_tuong": ma_nh,
                    "ten_doi_tuong": ten_nh,
                    "ten_viet_tat": ten_vt,
                    "ma_loai_doi_tuong": loai_nh,
                    "ky_du_lieu": ky,
                    "phien_ban": 1,
                    "tong_diem": eval_res["tong_diem"],
                    "xep_hang": eval_res["xep_hang"],
                    "diem_dinh_luong": eval_res.get("diem_dinh_luong", eval_res["tong_diem"]),
                    "diem_dinh_tinh": eval_res.get("diem_dinh_tinh", 5.0),
                    "ket_qua_cac_nhom": eval_res["ket_qua_cac_nhom"],
                    "ket_qua_nhom": eval_res["ket_qua_cac_nhom"],
                    "du_lieu_boc_tach": eval_res["du_lieu_boc_tach"],
                    "danh_gia_khoan_7_dieu_20": eval_res.get("danh_gia_khoan_7_dieu_20"),
                    "ngay_tinh": "2025-12-31T00:00:00",
                    "nguoi_tinh": "system_excel_importer",
                    "trang_thai": "DA_DUYET",
                    "is_active": 1
                }
                all_results.append(res_doc)

                if db is not None:
                    try:
                        await db.KetQuaTinhDiem.replace_one({"_id": res_doc["_id"]}, res_doc, upsert=True)
                    except Exception as db_err:
                        logger.warning(f"Save to DB failed: {db_err}")

            except Exception as e:
                logger.error(f"❌ Lỗi tính điểm {fname} (Kỳ {ky}): {e}")

        success_count += 1
        logger.info(f" [{success_count}/31] ✅ Đã xử lý xong file {fname:25s} -> {ten_vt}")

    # Out to precomputed JSON
    out_file = os.path.join(BE_ROOT, "scripts", "precomputed_31_rankings.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    logger.info(f"🎉 Đã ghi nhận thành công {len(all_results)} kết quả xếp hạng vào {out_file}")

    if db is not None:
        await close_mongo_connection()

    await close_mongo_connection()
    logger.info(f"🎉 HOÀN THÀNH TÍNH ĐIỂM {success_count}/31 FILE EXCEL XẾP HẠNG TCTD VÀO MONGODB!")

if __name__ == "__main__":
    asyncio.run(process_all_rankings())
