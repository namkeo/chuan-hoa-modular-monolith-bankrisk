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
logger = logging.getLogger("seed_qualitative_all")

def make_muc_diem_dinh_tinh_chung(n1, n2, n3, n4):
    return [
        {"thu_tu": 1, "diem": 5, "tu": None, "bao_gom_tu": False, "den": n1, "bao_gom_den": True},
        {"thu_tu": 2, "diem": 4, "tu": n1, "bao_gom_tu": False, "den": n2, "bao_gom_den": True},
        {"thu_tu": 3, "diem": 3, "tu": n2, "bao_gom_tu": False, "den": n3, "bao_gom_den": True},
        {"thu_tu": 4, "diem": 2, "tu": n3, "bao_gom_tu": False, "den": n4, "bao_gom_den": True},
        {"thu_tu": 5, "diem": 1, "tu": n4, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
    ]

async def run_load_all_qualitative():
    logger.info(f"Kết nối tới MongoDB tại {settings.MONGO_URI}...")
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 1. Cập nhật trọng số nhóm định tính trong NhomTieuChi
    await db.NhomTieuChi.update_one({"_id": "NTC_C"}, {"$set": {"trong_so_nhom_dinh_tinh": 5.0}})
    await db.NhomTieuChi.update_one({"_id": "NTC_A"}, {"$set": {"trong_so_nhom_dinh_tinh": 5.0}})
    await db.NhomTieuChi.update_one({"_id": "NTC_M"}, {"$set": {"trong_so_nhom_dinh_tinh": 7.0}})
    await db.NhomTieuChi.update_one({"_id": "NTC_E"}, {"$set": {"trong_so_nhom_dinh_tinh": 5.0}})
    await db.NhomTieuChi.update_one({"_id": "NTC_L"}, {"$set": {"trong_so_nhom_dinh_tinh": 5.0}})
    await db.NhomTieuChi.update_one({"_id": "NTC_S"}, {"$set": {"trong_so_nhom_dinh_tinh": 3.0}})
    logger.info("Đã cập nhật trong_so_nhom_dinh_tinh cho cả 6 nhóm CAMEL!")

    # 2. Xóa các chỉ tiêu định tính cũ
    dt_ids = ["CT_C_DT", "CT_A_DT", "CT_M_DT", "CT_E_DT", "CT_L_DT", "CT_S_DT"]
    await db.ChiTieu.delete_many({"_id": {"$in": dt_ids}})

    # -------------------------------------------------------------
    # 1. CHỈ TIÊU ĐỊNH TÍNH VỐN (C_DT)
    # -------------------------------------------------------------
    ct_c_dt = {
        "_id": "CT_C_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_C",
        "ma_chi_tieu": "C_DT",
        "ma_chi_tieu_goc": "C_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm VỐN (C)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Vốn căn cứ trên việc tuân thủ các quy định pháp luật và dữ liệu sai phạm thu thập được.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {"ma_noidung": "C_DT.a", "ten_noidung": "Tuân thủ các quy định pháp luật về ban hành, rà soát, xem xét sửa đổi, bổ sung, báo cáo Quy định nội bộ về đánh giá chất lượng tài sản có và tuân thủ tỷ lệ an toàn vốn tối thiểu theo quy định;"},
            {"ma_noidung": "C_DT.b", "ten_noidung": "Tuân thủ tỷ lệ an toàn vốn tối thiểu theo quy định;"},
            {"ma_noidung": "C_DT.c", "ten_noidung": "Tuân thủ các quy định pháp luật về giá trị thực của vốn điều lệ, vốn được cấp;"},
            {"ma_noidung": "C_DT.d", "ten_noidung": "Tuân thủ các quy định pháp luật về đánh giá nội bộ về mức đủ vốn."}
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TINH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {"ma_loai_doi_tuong": "ALL", "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng", "trong_so": 100.0, "cac_muc_diem": make_muc_diem_dinh_tinh_chung(0.50, 1.00, 1.50, 2.00)}
        ],
        "noi_dung_cham_diem": "Chấm điểm tự động dựa trên danh sách sai phạm thu thập được theo Điều 16a TT52 / TT23.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # 2. CHỈ TIÊU ĐỊNH TÍNH CHẤT LƯỢNG TÀI SẢN (A_DT)
    # -------------------------------------------------------------
    ct_a_dt = {
        "_id": "CT_A_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_A",
        "ma_chi_tieu": "A_DT",
        "ma_chi_tieu_goc": "A_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm CHẤT LƯỢNG TÀI SẢN (A)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Chất lượng tài sản căn cứ trên việc tuân thủ các quy định pháp luật và dữ liệu sai phạm thu thập được.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {"ma_noidung": "A_DT.a", "ten_noidung": "Tuân thủ các quy định của pháp luật về hoạt động cấp tín dụng;"},
            {"ma_noidung": "A_DT.b", "ten_noidung": "Tuân thủ các quy định pháp luật về ban hành, rà soát, sửa đổi, bổ sung và báo cáo quy định nội bộ về cấp tín dụng, quản lý tiền vay, chính sách dự phòng rủi ro;"},
            {"ma_noidung": "A_DT.c", "ten_noidung": "Tuân thủ các quy định pháp luật về hệ thống xếp hạng tín dụng nội bộ;"},
            {"ma_noidung": "A_DT.d", "ten_noidung": "Tuân thủ các quy định pháp luật về phân loại tài sản có, mức trích, phương pháp trích lập dự phòng rủi ro và việc sử dụng dự phòng rủi ro để xử lý rủi ro trong hoạt động của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài;"},
            {"ma_noidung": "A_DT.đ", "ten_noidung": "Tuân thủ các quy định pháp luật về trích lập và sử dụng các khoản dự phòng tổn thất các khoản đầu tư tài chính, nợ phải thu khó đòi;"},
            {"ma_noidung": "A_DT.e", "ten_noidung": "Tuân thủ các quy định của pháp luật về trích lập và sử dụng dự phòng rủi ro đối với trái phiếu đặc biệt do công ty quản lý tài sản của các tổ chức tín dụng Việt Nam phát hành;"},
            {"ma_noidung": "A_DT.g", "ten_noidung": "Tuân thủ các quy định pháp luật về hạn chế và giới hạn cấp tín dụng;"},
            {"ma_noidung": "A_DT.h", "ten_noidung": "Tuân thủ các quy định pháp luật về quản lý rủi ro tín dụng."}
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TINH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {"ma_loai_doi_tuong": "ALL", "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng", "trong_so": 100.0, "cac_muc_diem": make_muc_diem_dinh_tinh_chung(0.50, 1.00, 1.75, 2.75)}
        ],
        "noi_dung_cham_diem": "Chấm điểm tự động dựa trên danh sách sai phạm thu thập được theo Điều 16a TT52 / TT23.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # 3. CHỈ TIÊU ĐỊNH TÍNH QUẢN TRỊ ĐIỀU HÀNH (M_DT)
    # -------------------------------------------------------------
    ct_m_dt = {
        "_id": "CT_M_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_M",
        "ma_chi_tieu": "M_DT",
        "ma_chi_tieu_goc": "M_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm QUẢN TRỊ ĐIỀU HÀNH (M)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Quản trị điều hành căn cứ trên việc tuân thủ các quy định pháp luật và dữ liệu sai phạm thu thập được.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {"ma_noidung": "M_DT.a", "ten_noidung": "Tuân thủ các quy định pháp luật về cổ đông, cổ phần, cổ phiếu;"},
            {"ma_noidung": "M_DT.b", "ten_noidung": "Tuân thủ các quy định pháp luật về giới hạn góp vốn, mua cổ phần;"},
            {"ma_noidung": "M_DT.c", "ten_noidung": "Tuân thủ các quy định pháp luật về Hội đồng quản trị, Hội đồng thành viên, Ban Kiểm soát, Ban điều hành và các quy định pháp luật khác về quản trị, điều hành của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài;"},
            {"ma_noidung": "M_DT.d", "ten_noidung": "Tuân thủ các quy định pháp luật về hệ thống kiểm soát nội bộ bao gồm giám sát của quản lý cấp cao, kiểm soát nội bộ, kiểm toán nội bộ và quản lý rủi ro (không bao gồm quản lý rủi ro tín dụng, quản lý rủi ro thanh khoản, quản lý rủi ro thị trường) của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài;"},
            {"ma_noidung": "M_DT.đ", "ten_noidung": "Tuân thủ các quy định pháp luật về kiểm toán độc lập;"},
            {"ma_noidung": "M_DT.e", "ten_noidung": "Tuân thủ các quy định pháp luật về chế độ thông tin, báo cáo;"},
            {"ma_noidung": "M_DT.g", "ten_noidung": "Tuân thủ các quy định pháp luật về tiền tệ, ngân hàng khác ngoài các quy định đã được đề cập tại các chỉ tiêu định tính quy định tại Điều 7, 8, 10, 11, 12 Thông tư này và điểm a, b, c, d, đ, e khoản 2 Điều 9."}
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TINH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {"ma_loai_doi_tuong": "ALL", "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng", "trong_so": 100.0, "cac_muc_diem": make_muc_diem_dinh_tinh_chung(0.50, 0.75, 1.00, 1.50)}
        ],
        "noi_dung_cham_diem": "Chấm điểm tự động dựa trên danh sách sai phạm thu thập được theo Điều 16a TT52 / TT23.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # 4. CHỈ TIÊU ĐỊNH TÍNH KẾT QUẢ HOẠT ĐỘNG KINH DOANH (E_DT)
    # -------------------------------------------------------------
    ct_e_dt = {
        "_id": "CT_E_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_E",
        "ma_chi_tieu": "E_DT",
        "ma_chi_tieu_goc": "E_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm KẾT QUẢ HOẠT ĐỘNG KINH DOANH (E)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Kết quả hoạt động kinh doanh căn cứ trên việc tuân thủ các quy định pháp luật và dữ liệu sai phạm thu thập được.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {"ma_noidung": "E_DT.a", "ten_noidung": "Tuân thủ quy định pháp luật về chế độ tài chính đối với tổ chức tín dụng, chi nhánh ngân hàng nước ngoài."}
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TINH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {"ma_loai_doi_tuong": "ALL", "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng", "trong_so": 100.0, "cac_muc_diem": make_muc_diem_dinh_tinh_chung(1.00, 2.00, 5.00, 8.00)}
        ],
        "noi_dung_cham_diem": "Chấm điểm tự động dựa trên danh sách sai phạm thu thập được theo Điều 16a TT52 / TT23.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # 5. CHỈ TIÊU ĐỊNH TÍNH KHẢ NĂNG THANH KHOẢN (L_DT)
    # -------------------------------------------------------------
    ct_l_dt = {
        "_id": "CT_L_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_L",
        "ma_chi_tieu": "L_DT",
        "ma_chi_tieu_goc": "L_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm KHẢ NĂNG THANH KHOẢN (L)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Khả năng thanh khoản căn cứ trên việc tuân thủ các quy định pháp luật và dữ liệu sai phạm thu thập được.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {"ma_noidung": "L_DT.a", "ten_noidung": "Tuân thủ các quy định pháp luật về tỷ lệ khả năng chi trả, tỷ lệ tối đa của nguồn vốn ngắn hạn được sử dụng để cho vay trung hạn và dài hạn, tỷ lệ dư nợ cho vay so với tổng tiền gửi;"},
            {"ma_noidung": "L_DT.b", "ten_noidung": "Tuân thủ các quy định pháp luật về ban hành, rà soát, sửa đổi, bổ sung và báo cáo quy định nội bộ về quản lý thanh khoản và tuân thủ các quy định pháp luật khác về quản lý rủi ro thanh khoản."}
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TINH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {"ma_loai_doi_tuong": "ALL", "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng", "trong_so": 100.0, "cac_muc_diem": make_muc_diem_dinh_tinh_chung(1.50, 3.00, 6.00, 9.00)}
        ],
        "noi_dung_cham_diem": "Chấm điểm tự động dựa trên danh sách sai phạm thu thập được theo Điều 16a TT52 / TT23.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    # -------------------------------------------------------------
    # 6. CHỈ TIÊU ĐỊNH TÍNH MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (S_DT)
    # -------------------------------------------------------------
    ct_s_dt = {
        "_id": "CT_S_DT",
        "bo_tieu_chi_id": "BTC_2026_V1",
        "nhom_tieu_chi_id": "NTC_S",
        "ma_chi_tieu": "S_DT",
        "ma_chi_tieu_goc": "S_DT",
        "ten_chi_tieu": "Đánh giá định tính nhóm MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (S)",
        "mo_ta_cong_thuc": "Điểm định tính nhóm Mức độ nhạy cảm với rủi ro thị trường căn cứ trên việc tuân thủ các quy định pháp luật và dữ liệu sai phạm thu thập được.",
        "cong_thuc": None,
        "danh_sach_bien": [],
        "danh_sach_noi_dung_dinh_tinh": [
            {"ma_noidung": "S_DT.a", "ten_noidung": "Tuân thủ giới hạn tổng trạng thái ngoại tệ theo quy định của pháp luật;"},
            {"ma_noidung": "S_DT.b", "ten_noidung": "Tuân thủ các quy định pháp luật về quản lý rủi ro thị trường."}
        ],
        "don_vi_tinh": "điểm",
        "loai_chi_tieu": "DINH_TINH",
        "dieu_kien_ap_dung": {"kieu": "LUON_DUNG"},
        "cau_hinh_theo_doi_tuong": [
            {"ma_loai_doi_tuong": "ALL", "ten_loai_doi_tuong": "Áp dụng chung cho tất cả tổ chức tín dụng", "trong_so": 100.0, "cac_muc_diem": make_muc_diem_dinh_tinh_chung(3.00, 4.00, 5.00, 6.00)}
        ],
        "noi_dung_cham_diem": "Chấm điểm tự động dựa trên danh sách sai phạm thu thập được theo Điều 16a TT52 / TT23.",
        "can_cu_phap_ly": "Điều 16a TT52 đã được bổ sung bởi TT23",
        "thu_tu_hien_thi": 99,
        "is_active": 1
    }

    all_dt = [ct_c_dt, ct_a_dt, ct_m_dt, ct_e_dt, ct_l_dt, ct_s_dt]
    await db.ChiTieu.insert_many(all_dt)
    logger.info("🎉 Đã nạp thành công 6 chỉ tiêu định tính chính thức (loai_chi_tieu=DINH_TINH, ma_noidung=C_DT.a, A_DT.a...)!")

if __name__ == "__main__":
    asyncio.run(run_load_all_qualitative())
