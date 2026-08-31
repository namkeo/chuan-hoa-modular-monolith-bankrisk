import sys
import os
import json
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parent.parent
if str(BE_ROOT) not in sys.path:
    sys.path.insert(0, str(BE_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

from app.utils.template_dl_read import extract_camels_data
from app.utils.camels_full_evaluator import evaluate_full_camels_from_excel

def resolve_excel_folder() -> str:
    peer_dir = BE_ROOT.parent / "minio_data" / "xep_hang_tctd"
    if peer_dir.exists() and list(peer_dir.glob("XH_TCTD_*.xlsx")):
        return str(peer_dir)
    return r"D:\Văn bản KTNN\Rủi ro vốn\[SBV] Tài liệu khảo sát\dataset\source_code\minio_data\xep_hang_tctd"

EXCEL_FOLDER = resolve_excel_folder()

# Bản đồ 31 TCTD từ DS_TCTD.xlsx và file Excel tương ứng
EXCEL_FILE_MAP = [
    ("XH_TCTD_VTB.xlsx", "VietinBank", "Ngân hàng TMCP Công thương Việt Nam", "VietinBank (CTG)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_BIDV.xlsx", "BIDV", "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam", "BIDV (BID)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_Agribank.xlsx", "Agribank", "Ngân hàng Nông nghiệp và Phát triển Nông thôn Việt Nam", "Agribank (AGR)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_VCB.xlsx", "Vietcombank", "Ngân hàng TMCP Ngoại thương Việt Nam", "Vietcombank (VCB)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_ACB.xlsx", "ACB", "Ngân hàng TMCP Á Châu", "ACB", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_LPB.xlsx", "LPBank", "Ngân hàng TMCP Lộc Phát Việt Nam", "LPBank (LPB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_TCB.xlsx", "Techcombank", "Ngân hàng TMCP Kỹ Thương Việt Nam", "Techcombank (TCB)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_HDB.xlsx", "HDBank", "Ngân hàng TMCP Phát triển TP.HCM", "HDBank (HDB)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_MB.xlsx", "MBBank", "Ngân hàng TMCP Quân Đội", "MBBank (MBB)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_VIB.xlsx", "VIB", "Ngân hàng TMCP Quốc tế Việt Nam", "VIB", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_SHB.xlsx", "SHB", "Ngân hàng TMCP Sài Gòn - Hà Nội", "SHB", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_TPB.xlsx", "TPBank", "Ngân hàng TMCP Tiên Phong", "TPBank (TPB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_VPB.xlsx", "VPBank", "Ngân hàng TMCP Việt Nam Thịnh Vượng", "VPBank (VPB)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_BACABANK.xlsx", "Bac A Bank", "Ngân hàng TMCP Bắc Á", "Bac A Bank (BAB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_MSB.xlsx", "MSB", "Ngân hàng TMCP Hàng Hải Việt Nam", "MSB", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_VAB.xlsx", "VietABank", "Ngân hàng TMCP Việt Á", "VietABank (VAB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_SeABank.xlsx", "SeABank", "Ngân hàng TMCP Đông Nam Á", "SeABank (SSB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_BVBank.xlsx", "BVBank", "Ngân hàng TMCP Bản Việt", "BVBank (BVB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_EximBank.xlsx", "Eximbank", "Ngân hàng TMCP Xuất nhập khẩu Việt Nam", "Eximbank (EIB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_NCB.xlsx", "NCB", "Ngân hàng TMCP Quốc Dân", "NCB (NVB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_NAB.xlsx", "Nam A Bank", "Ngân hàng TMCP Nam Á", "Nam A Bank (NAB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_OCB.xlsx", "OCB", "Ngân hàng TMCP Phương Đông", "OCB", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_BaoVietBank.xlsx", "BaoVietBank", "Ngân hàng TMCP Bảo Việt", "BaoVietBank (BAOVIET)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_PGBank.xlsx", "PGBank", "Ngân hàng TMCP Thịnh Vượng và Phát triển", "PGBank (PGB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_SGB.xlsx", "SaigonBank", "Ngân hàng TMCP Sài Gòn Công thương", "SaigonBank (SGB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_ABBank.xlsx", "ABBank", "Ngân hàng TMCP An Bình", "ABBank (ABB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_Vietbank.xlsx", "Vietbank", "Ngân hàng TMCP Việt Nam Thương Tín", "Vietbank (VBB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_KienlongBank.xlsx", "KienlongBank", "Ngân hàng TMCP Kiên Long", "KienlongBank (KLB)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_STB.xlsx", "Sacombank", "Ngân hàng TMCP Sài Gòn Thương Tín", "Sacombank (STB)", "NHTM_QUY_MO_LON"),
    ("XH_TCTD_PVcomBank.xlsx", "PVcomBank", "Ngân hàng TMCP Đại Chúng Việt Nam", "PVcomBank (PVC)", "NHTM_VUA_VA_NHO"),
    ("XH_TCTD_SCB.xlsx", "SCB", "Ngân hàng TMCP Sài Gòn", "SCB", "NHTM_VUA_VA_NHO")
]

BANK_QUALITATIVE_OVERRIDES = {
    "VietinBank": {
        "M": {
            "diem": 4.0,
            "dien_giai": "Đánh giá các chỉ tiêu định tính Nhóm M (Quản trị điều hành): 4.0 điểm",
            "details": {"so_luong_sai_pham": 0}
        }
    }
}

def main():
    all_results = []
    periods = ["2025"]

    for fname, ma_nh, ten_nh, ten_vt, loai_nh in EXCEL_FILE_MAP:
        file_path = os.path.join(EXCEL_FOLDER, fname)
        if not os.path.exists(file_path):
            print(f"⚠️  File {fname} không tồn tại!")
            continue

        camels_rows = extract_camels_data(file_path)

        for ky in periods:
            dt_map = BANK_QUALITATIVE_OVERRIDES.get(ma_nh, {})
            eval_res = evaluate_full_camels_from_excel(camels_rows, ma_nh, ky, dt_scores_map=dt_map)

            doc = {
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
            all_results.append(doc)

        print(f"✅ {fname:25s} -> {ten_vt:20s} | Tổng điểm: {eval_res['tong_diem']:.2f} | Hạng: {eval_res['xep_hang']}")

    out_file = os.path.join(BE_ROOT, "scripts", "precomputed_31_rankings.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Đã xuất thành công {len(all_results)} kết quả xếp hạng vào {out_file}!")

if __name__ == "__main__":
    main()
