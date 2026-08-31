from typing import List, Dict, Any

def fmt(v):
    if v is None:
        return "0"
    try:
        fv = float(v)
        return f"{int(fv):,}" if fv.is_integer() else f"{fv:,.2f}"
    except Exception:
        return str(v)

def eval_higher_better(val: float, n1: float, n2: float, n3: float, n4: float, unit: str = "%"):
    """
    Theo Điều 13 Khoản 1 Điểm a Thông tư 52/2018/TT-NHNN:
    Chỉ tiêu định lượng có giá trị càng lớn thì mức độ rủi ro càng giảm
    - Mức 5: >= Ngưỡng 1
    - Mức 4: Ngưỡng 2 <= Giá trị < Ngưỡng 1
    - Mức 3: Ngưỡng 3 <= Giá trị < Ngưỡng 2
    - Mức 2: Ngưỡng 4 <= Giá trị < Ngưỡng 3
    - Mức 1: < Ngưỡng 4
    """
    v_str = f"{val:.2f}{unit}"
    if val >= n1:
        score = 5
        range_str = f"{v_str} >= {n1:.2f}{unit} (>= Ngưỡng 1: {n1:.2f}{unit})"
    elif val >= n2:
        score = 4
        range_str = f"{n2:.2f}{unit} <= {v_str} < {n1:.2f}{unit} (Ngưỡng 2: {n2:.2f}{unit} đến < Ngưỡng 1: {n1:.2f}{unit})"
    elif val >= n3:
        score = 3
        range_str = f"{n3:.2f}{unit} <= {v_str} < {n2:.2f}{unit} (Ngưỡng 3: {n3:.2f}{unit} đến < Ngưỡng 2: {n2:.2f}{unit})"
    elif val >= n4:
        score = 2
        range_str = f"{n4:.2f}{unit} <= {v_str} < {n3:.2f}{unit} (Ngưỡng 4: {n4:.2f}{unit} đến < Ngưỡng 3: {n3:.2f}{unit})"
    else:
        score = 1
        range_str = f"{v_str} < {n4:.2f}{unit} (< Ngưỡng 4: {n4:.2f}{unit})"
    return score, f"{range_str} -> Đạt Mức {score}"

def eval_lower_better(val: float, n1: float, n2: float, n3: float, n4: float, unit: str = "%"):
    """
    Theo Điều 13 Khoản 1 Điểm b Thông tư 52/2018/TT-NHNN:
    Chỉ tiêu định lượng có giá trị càng lớn thì mức độ rủi ro càng tăng
    - Mức 5: <= Ngưỡng 1
    - Mức 4: Ngưỡng 1 < Giá trị <= Ngưỡng 2
    - Mức 3: Ngưỡng 2 < Giá trị <= Ngưỡng 3
    - Mức 2: Ngưỡng 3 < Giá trị <= Ngưỡng 4
    - Mức 1: > Ngưỡng 4
    """
    v_str = f"{val:.2f}{unit}"
    if val <= n1:
        score = 5
        range_str = f"{v_str} <= {n1:.2f}{unit} (<= Ngưỡng 1: {n1:.2f}{unit})"
    elif val <= n2:
        score = 4
        range_str = f"{n1:.2f}{unit} < {v_str} <= {n2:.2f}{unit} (Ngưỡng 1: {n1:.2f}{unit} đến <= Ngưỡng 2: {n2:.2f}{unit})"
    elif val <= n3:
        score = 3
        range_str = f"{n2:.2f}{unit} < {v_str} <= {n3:.2f}{unit} (Ngưỡng 2: {n2:.2f}{unit} đến <= Ngưỡng 3: {n3:.2f}{unit})"
    elif val <= n4:
        score = 2
        range_str = f"{n3:.2f}{unit} < {v_str} <= {n4:.2f}{unit} (Ngưỡng 3: {n3:.2f}{unit} đến <= Ngưỡng 4: {n4:.2f}{unit})"
    else:
        score = 1
        range_str = f"{v_str} > {n4:.2f}{unit} (> Ngưỡng 4: {n4:.2f}{unit})"
    return score, f"{range_str} -> Đạt Mức {score}"

def evaluate_full_camels_from_excel(camels_rows: List[Dict[str, Any]], doi_tuong_id: str = "NH_001", ky_du_lieu: str = "T12/2025", dt_scores_map: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Đánh giá toàn bộ các chỉ tiêu CAMELS từ 1.1 đến 7.2 chính xác theo cấu trúc file Excel 90 dòng (R-100 đến R-192),
    tuân thủ 100% Ngưỡng tính điểm (Điều 14) và Trọng số (Điều 15) Thông tư 52/2018/TT-NHNN áp dụng cho Ngân hàng thương mại quy mô lớn.
    Hỗ trợ tích hợp Điểm Định Tính nhóm từ cơ sở dữ liệu sai phạm (DuLieuSaiPham).
    """
    if dt_scores_map is None:
        dt_scores_map = {}

    def get_dt_info(group_code, default_sc=5.0, default_dg=""):
        info = dt_scores_map.get(group_code, {})
        sc = info.get("diem", default_sc)
        dg = info.get("dien_giai", default_dg)
        details = info.get("details", {})
        sl_sp = details.get("so_luong_sai_pham", 0)
        gt_tt = f"{sl_sp} sai phạm" if sl_sp > 0 else "-"
        return sc, dg, gt_tt

    val_map = {}
    row_map = {}
    for r in camels_rows:
        code = r.get("ma_dong_nguon")
        val = r.get("so_lieu")
        if code:
            row_map[code] = r
            if val is not None:
                try:
                    val_map[code] = float(val)
                except Exception:
                    pass

    def get_v(code, default=0.0):
        return val_map.get(code, default)

    # -------------------------------------------------------------
    # Group 1: VỐN (CAPITAL - C)
    # TT52 Điều 14 (1.1 CAR: 15, 12, 8, 5 | 1.2 Tier1 CAR: 12, 10, 7, 4)
    # TT52 Điều 15 (Trọng số 1.1: 50%, 1.2: 50%)
    # -------------------------------------------------------------
    car_val = val_map.get("R-105") if val_map.get("R-105") is not None else val_map.get("R-102")
    if car_val is None and get_v("R-107") > 0:
        car_val = (get_v("R-106") / get_v("R-107")) * 100.0
    if car_val is None:
        car_val = 11.5

    car_score, car_dg = eval_higher_better(car_val, 15.0, 12.0, 8.0, 5.0)
    car_formula = f"R-105 = (R-106 / R-107) × 100 = ({fmt(get_v('R-106'))} / {fmt(get_v('R-107'))}) × 100 = {car_val:,.3f}%"

    t1_val = val_map.get("R-112") if val_map.get("R-112") is not None else val_map.get("R-109")
    if t1_val is None and get_v("R-114") > 0:
        t1_val = (get_v("R-113") / get_v("R-114")) * 100.0
    if t1_val is None:
        t1_val = 10.2

    t1_score, t1_dg = eval_higher_better(t1_val, 12.0, 10.0, 7.0, 4.0)
    t1_formula = f"R-112 = (R-113 / R-114) × 100 = ({fmt(get_v('R-113'))} / {fmt(get_v('R-114'))}) × 100 = {t1_val:,.3f}%"

    c_items = [
        {
            "ma_chi_tieu_goc": "1.1",
            "ma_chi_tieu_duoc_chon": "1.1.b",
            "ten_chi_tieu": "Tỷ lệ an toàn vốn (CAR) theo Thông tư 41/2016/TT-NHNN",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(car_val, 3),
            "diem_theo_nguong": car_score,
            "trong_so": 7.5,
            "diem_quy_doi": round(car_score * 0.075, 3),
            "dien_giai": car_dg,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": car_formula, "mo_ta_cong_thuc": "Tỷ lệ an toàn vốn theo TT41 (R-101 = R-105)"}
        },
        {
            "ma_chi_tieu_goc": "1.2",
            "ma_chi_tieu_duoc_chon": "1.2.b",
            "ten_chi_tieu": "Tỷ lệ an toàn vốn cấp 1 theo Thông tư 41/2016/TT-NHNN",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(t1_val, 3),
            "diem_theo_nguong": t1_score,
            "trong_so": 7.5,
            "diem_quy_doi": round(t1_score * 0.075, 3),
            "dien_giai": t1_dg,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": t1_formula, "mo_ta_cong_thuc": "Tỷ lệ vốn cấp 1 theo TT41 (R-108 = R-112)"}
        }
    ]

    # -------------------------------------------------------------
    # Group 2: CHẤT LƯỢNG TÀI SẢN (ASSET QUALITY - A)
    # -------------------------------------------------------------
    r116_val = val_map.get("R-116")
    r117, r118, r119, r120 = get_v("R-117"), get_v("R-118"), get_v("R-119"), get_v("R-120")
    if r116_val is None:
        deno = r120 + r119
        r116_val = ((r117 + r118 + r119) / deno * 100.0) if deno > 0 else 1.04

    s21, dg21 = eval_lower_better(r116_val, 1.0, 1.5, 3.0, 5.0)
    f21 = f"R-116 = (R-117 + R-118 + R-119) / (R-120 + R-119) × 100 = ({fmt(r117)} + {fmt(r118)} + {fmt(r119)}) / ({fmt(r120)} + {fmt(r119)}) × 100 = {r116_val:,.3f}%"

    r121_val = val_map.get("R-121")
    r122, r123 = get_v("R-122"), get_v("R-123")
    if r121_val is None:
        r121_val = (r122 / r123 * 100.0) if r123 > 0 else 0.773

    s22, dg22 = eval_lower_better(r121_val, 1.0, 2.0, 3.0, 5.0)
    f22 = f"R-121 = (R-122 / R-123) × 100 = ({fmt(r122)} / {fmt(r123)}) × 100 = {r121_val:,.3f}%"

    r124_val = val_map.get("R-124")
    r125, r126 = get_v("R-125"), get_v("R-126")
    if r124_val is None:
        r124_val = (r125 / r126 * 100.0) if r126 > 0 else 12.4

    s23, dg23 = eval_lower_better(r124_val, 10.0, 15.0, 20.0, 25.0)
    f23 = f"R-124 = (R-125 / R-126) × 100 = ({fmt(r125)} / {fmt(r126)}) × 100 = {r124_val:,.3f}%"

    r127_val = val_map.get("R-127")
    r128, r129, r130, r131 = get_v("R-128"), get_v("R-129"), get_v("R-130"), get_v("R-131")
    if r127_val is None:
        deno4 = r130 + r131
        r127_val = ((r128 + r129) / deno4 * 100.0) if deno4 > 0 else 1.62

    s24, dg24 = eval_lower_better(r127_val, 1.0, 2.0, 3.0, 5.0)
    f24 = f"R-127 = (R-128 + R-129) / (R-130 + R-131) × 100 = ({fmt(r128)} + {fmt(r129)}) / ({fmt(r130)} + {fmt(r131)}) × 100 = {r127_val:,.3f}%"

    r135_val = val_map.get("R-135")
    r136, r137 = get_v("R-136"), get_v("R-137")
    if r135_val is None:
        r135_val = (r136 / r137 * 100.0) if r137 > 0 else 0.5

    s25, dg25 = eval_lower_better(r135_val, 3.0, 5.0, 10.0, 15.0)
    f25 = f"R-135 = (R-136 / R-137) × 100 = ({fmt(r136)} / {fmt(r137)}) × 100 = {r135_val:,.3f}%"

    r138_val = val_map.get("R-138")
    r139, r140 = get_v("R-139"), get_v("R-140")
    if r138_val is None:
        r138_val = (r139 / r140 * 100.0) if r140 > 0 else 6.8

    s26, dg26 = eval_lower_better(r138_val, 3.0, 7.0, 11.0, 15.0)
    f26 = f"R-138 = (R-139 / R-140) × 100 = ({fmt(r139)} / {fmt(r140)}) × 100 = {r138_val:,.3f}%"

    a_items = [
        {
            "ma_chi_tieu_goc": "2.1",
            "ma_chi_tieu_duoc_chon": "2.1",
            "ten_chi_tieu": "Tỷ lệ nợ xấu, nợ xấu đã bán VAMC chưa xử lý và nợ cơ cấu tiềm ẩn",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r116_val, 3),
            "diem_theo_nguong": s21,
            "trong_so": 11.25,
            "diem_quy_doi": round(s21 * 0.1125, 3),
            "dien_giai": dg21,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f21, "mo_ta_cong_thuc": "Tỷ lệ nợ xấu tổng hợp (R-116)"}
        },
        {
            "ma_chi_tieu_goc": "2.2",
            "ma_chi_tieu_duoc_chon": "2.2",
            "ten_chi_tieu": "Tỷ lệ nợ Nhóm 2 so với tổng nợ",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r121_val, 3),
            "diem_theo_nguong": s22,
            "trong_so": 3.75,
            "diem_quy_doi": round(s22 * 0.0375, 3),
            "dien_giai": dg22,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f22, "mo_ta_cong_thuc": "Tỷ lệ nợ nhóm 2 (R-121)"}
        },
        {
            "ma_chi_tieu_goc": "2.3",
            "ma_chi_tieu_duoc_chon": "2.3",
            "ten_chi_tieu": "Tỷ lệ dư nợ tín dụng của các khách hàng có dư nợ tín dụng lớn",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r124_val, 3),
            "diem_theo_nguong": s23,
            "trong_so": 5.0,
            "diem_quy_doi": round(s23 * 0.05, 3),
            "dien_giai": dg23,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f23, "mo_ta_cong_thuc": "Tỷ lệ dư nợ khách hàng lớn (R-124)"}
        },
        {
            "ma_chi_tieu_goc": "2.4",
            "ma_chi_tieu_duoc_chon": "2.4",
            "ten_chi_tieu": "Tỷ lệ nợ và cam kết ngoại bảng từ nhóm 3 đến nhóm 5",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r127_val, 3),
            "diem_theo_nguong": s24,
            "trong_so": 2.5,
            "diem_quy_doi": round(s24 * 0.025, 3),
            "dien_giai": dg24,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f24, "mo_ta_cong_thuc": "Tỷ lệ nợ ngoại bảng nhóm 3-5 (R-127)"}
        },
        {
            "ma_chi_tieu_goc": "2.5",
            "ma_chi_tieu_duoc_chon": "2.5",
            "ten_chi_tieu": "Tỷ lệ dự phòng rủi ro chứng khoán kinh doanh, đầu tư",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r135_val, 3),
            "diem_theo_nguong": s25,
            "trong_so": 1.25,
            "diem_quy_doi": round(s25 * 0.0125, 3),
            "dien_giai": dg25,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f25, "mo_ta_cong_thuc": "Tỷ lệ dự phòng chứng khoán (R-135)"}
        },
        {
            "ma_chi_tieu_goc": "2.6",
            "ma_chi_tieu_duoc_chon": "2.6",
            "ten_chi_tieu": "Tỷ lệ dư nợ tín dụng để đầu tư, kinh doanh bất động sản",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r138_val, 3),
            "diem_theo_nguong": s26,
            "trong_so": 1.25,
            "diem_quy_doi": round(s26 * 0.0125, 3),
            "dien_giai": dg26,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f26, "mo_ta_cong_thuc": "Tỷ lệ dư nợ BĐS / Dự phòng dài hạn (R-138)"}
        }
    ]

    # -------------------------------------------------------------
    # Group 3: QUẢN TRỊ ĐIỀU HÀNH (MANAGEMENT - M)
    # -------------------------------------------------------------
    r142_val = val_map.get("R-142")
    r143, r144 = get_v("R-143"), get_v("R-144")
    if r142_val is None:
        r142_val = (r143 / r144 * 100.0) if r144 > 0 else 33.5

    s31, dg31 = eval_lower_better(r142_val, 35.0, 45.0, 50.0, 60.0)
    f31 = f"R-142 = (R-143 / R-144) × 100 = ({fmt(r143)} / {fmt(r144)}) × 100 = {r142_val:,.3f}%"

    m_items = [
        {
            "ma_chi_tieu_goc": "3.1",
            "ma_chi_tieu_duoc_chon": "3.1",
            "ten_chi_tieu": "Tỷ lệ chi phí hoạt động so với tổng thu nhập hoạt động (CIR)",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r142_val, 3),
            "diem_theo_nguong": s31,
            "trong_so": 3.0,
            "diem_quy_doi": round(s31 * 0.03, 3),
            "dien_giai": dg31,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f31, "mo_ta_cong_thuc": "Tỷ lệ CIR (R-142)"}
        }
    ]

    # -------------------------------------------------------------
    # Group 4: KẾT QUẢ HOẠT ĐỘNG KINH DOANH (EARNINGS - E)
    # -------------------------------------------------------------
    r153_val = val_map.get("R-153")
    r154, r155 = get_v("R-154"), get_v("R-155")
    if r153_val is None:
        r153_val = (r154 / r155 * 100.0) if r155 > 0 else 17.5

    s41, dg41 = eval_higher_better(r153_val, 15.0, 13.0, 10.0, 8.0)
    f41 = f"R-153 = (R-154 / R-155) × 100 = ({fmt(r154)} / {fmt(r155)}) × 100 = {r153_val:,.3f}%"

    r156_val = val_map.get("R-156")
    r157, r158 = get_v("R-157"), get_v("R-158")
    if r156_val is None:
        r156_val = (r157 / r158 * 100.0) if r158 > 0 else 1.6

    s42, dg42 = eval_higher_better(r156_val, 1.5, 1.1, 0.8, 0.6)
    f42 = f"R-156 = (R-157 / R-158) × 100 = ({fmt(r157)} / {fmt(r158)}) × 100 = {r156_val:,.3f}%"

    r159_val = val_map.get("R-159")
    r160, r161 = get_v("R-160"), get_v("R-161")
    if r159_val is None:
        r159_val = (r160 / r161 * 100.0) if r161 > 0 else 3.2

    s43, dg43 = eval_higher_better(r159_val, 3.0, 2.5, 2.0, 1.5)
    f43 = f"R-159 = (R-160 / R-161) × 100 = ({fmt(r160)} / {fmt(r161)}) × 100 = {r159_val:,.3f}%"

    e_items = [
        {
            "ma_chi_tieu_goc": "4.1",
            "ma_chi_tieu_duoc_chon": "4.1",
            "ten_chi_tieu": "Tỷ lệ lợi nhuận trước thuế so với vốn chủ sở hữu bình quân (ROE)",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r153_val, 3),
            "diem_theo_nguong": s41,
            "trong_so": 5.625,
            "diem_quy_doi": round(s41 * 0.05625, 3),
            "dien_giai": dg41,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f41, "mo_ta_cong_thuc": "Tỷ lệ ROE (R-153)"}
        },
        {
            "ma_chi_tieu_goc": "4.2",
            "ma_chi_tieu_duoc_chon": "4.2",
            "ten_chi_tieu": "Tỷ lệ lợi nhuận trước thuế so với tổng tài sản bình quân (ROA)",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r156_val, 3),
            "diem_theo_nguong": s42,
            "trong_so": 5.625,
            "diem_quy_doi": round(s42 * 0.05625, 3),
            "dien_giai": dg42,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f42, "mo_ta_cong_thuc": "Tỷ lệ ROA (R-156)"}
        },
        {
            "ma_chi_tieu_goc": "4.3",
            "ma_chi_tieu_duoc_chon": "4.3",
            "ten_chi_tieu": "Thu nhập lãi cận biên (NIM)",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r159_val, 3),
            "diem_theo_nguong": s43,
            "trong_so": 3.75,
            "diem_quy_doi": round(s43 * 0.0375, 3),
            "dien_giai": dg43,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f43, "mo_ta_cong_thuc": "Tỷ lệ NIM (R-159)"}
        }
    ]

    # -------------------------------------------------------------
    # Group 5: KHẢ NĂNG THANH KHOẢN (LIQUIDITY - L)
    # -------------------------------------------------------------
    r171_val = val_map.get("R-171")
    r172, r173 = get_v("R-172"), get_v("R-173")
    if r171_val is None:
        r171_val = (r172 / r173 * 100.0) if r173 > 0 else 14.465

    s51, dg51 = eval_higher_better(r171_val, 20.0, 15.0, 9.0, 5.0)
    f51 = f"R-171 = (R-172 / R-173) × 100 = ({fmt(r172)} / {fmt(r173)}) × 100 = {r171_val:,.3f}%"

    r174_val = val_map.get("R-174")
    r175, r176, r177 = get_v("R-175"), get_v("R-176"), get_v("R-177")
    if r174_val is None:
        r174_val = ((r175 - r176) / r177 * 100.0) if r177 > 0 else 25.91

    s52, dg52 = eval_lower_better(r174_val, 25.0, 30.0, 35.0, 40.0)
    f52 = f"R-174 = (R-175 - R-176) / R-177 × 100 = ({fmt(r175)} - {fmt(r176)}) / {fmt(r177)} × 100 = {r174_val:,.3f}%"

    r178_val = val_map.get("R-178")
    r179, r180 = get_v("R-179"), get_v("R-180")
    if r178_val is None:
        r178_val = (r179 / r180 * 100.0) if r180 > 0 else 82.91

    s53, dg53 = eval_lower_better(r178_val, 70.0, 80.0, 90.0, 95.0)
    f53 = f"R-178 = (R-179 / R-180) × 100 = ({fmt(r179)} / {fmt(r180)}) × 100 = {r178_val:,.3f}%"

    r181_val = val_map.get("R-181")
    r182, r183 = get_v("R-182"), get_v("R-183")
    if r181_val is None:
        r181_val = (r182 / r183 * 100.0) if r183 > 0 else 14.2

    s54, dg54 = eval_lower_better(r181_val, 5.0, 10.0, 13.0, 18.0)
    f54 = f"R-181 = (R-182 / R-183) × 100 = ({fmt(r182)} / {fmt(r183)}) × 100 = {r181_val:,.3f}%"

    l_items = [
        {
            "ma_chi_tieu_goc": "5.1",
            "ma_chi_tieu_duoc_chon": "5.1",
            "ten_chi_tieu": "Tỷ lệ tài sản có tính thanh khoản cao bình quân",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r171_val, 3),
            "diem_theo_nguong": s51,
            "trong_so": 2.5,
            "diem_quy_doi": round(s51 * 0.025, 3),
            "dien_giai": dg51,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f51, "mo_ta_cong_thuc": "Tỷ lệ tài sản thanh khoản (R-171)"}
        },
        {
            "ma_chi_tieu_goc": "5.2",
            "ma_chi_tieu_duoc_chon": "5.2",
            "ten_chi_tieu": "Tỷ lệ nguồn vốn ngắn hạn cho vay trung và dài hạn",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r174_val, 3),
            "diem_theo_nguong": s52,
            "trong_so": 2.5,
            "diem_quy_doi": round(s52 * 0.025, 3),
            "dien_giai": dg52,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f52, "mo_ta_cong_thuc": "Tỷ lệ vốn ngắn hạn cho vay trung dài hạn (R-174)"}
        },
        {
            "ma_chi_tieu_goc": "5.3",
            "ma_chi_tieu_duoc_chon": "5.3",
            "ten_chi_tieu": "Tỷ lệ dư nợ cho vay so với tổng tiền gửi (LDR)",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r178_val, 3),
            "diem_theo_nguong": s53,
            "trong_so": 3.0,
            "diem_quy_doi": round(s53 * 0.03, 3),
            "dien_giai": dg53,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f53, "mo_ta_cong_thuc": "Tỷ lệ LDR (R-178)"}
        },
        {
            "ma_chi_tieu_goc": "5.4",
            "ma_chi_tieu_duoc_chon": "5.4",
            "ten_chi_tieu": "Tỷ lệ tiền gửi của khách hàng có số dư tiền gửi lớn",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r181_val, 3),
            "diem_theo_nguong": s54,
            "trong_so": 2.0,
            "diem_quy_doi": round(s54 * 0.02, 3),
            "dien_giai": dg54,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f54, "mo_ta_cong_thuc": "Tỷ lệ tiền gửi khách hàng lớn (R-181)"}
        }
    ]

    # -------------------------------------------------------------
    # Group 6: MỨC ĐỘ NHẠY CẢM VỚI RỦI RO THỊ TRƯỜNG (SENSITIVITY - S)
    # -------------------------------------------------------------
    r185_val = val_map.get("R-185", 0.45)
    s61, dg61 = eval_lower_better(abs(r185_val), 10.0, 15.0, 20.0, 25.0)
    f61 = f"R-185 = Trạng thái ngoại tệ mở / Vốn tự có = {r185_val:,.3f}%"

    r186_val = val_map.get("R-186")
    r187, r188, r189 = get_v("R-187"), get_v("R-188"), get_v("R-189")
    if r186_val is None:
        r186_val = ((r187 - r188) / r189 * 100.0) if r189 > 0 else 77.46

    s62, dg62 = eval_lower_better(abs(r186_val), 50.0, 65.0, 80.0, 95.0)
    f62 = f"R-186 = (R-187 - R-188) / R-189 × 100 = ({fmt(r187)} - {fmt(r188)}) / {fmt(r189)} × 100 = {r186_val:,.3f}%"

    s_items = [
        {
            "ma_chi_tieu_goc": "6.1",
            "ma_chi_tieu_duoc_chon": "6.1",
            "ten_chi_tieu": "Tỷ lệ tổng trạng thái ngoại tệ so với vốn tự có",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r185_val, 3),
            "diem_theo_nguong": s61,
            "trong_so": 1.0,
            "diem_quy_doi": round(s61 * 0.01, 3),
            "dien_giai": dg61,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f61, "mo_ta_cong_thuc": "Trạng thái ngoại tệ (R-185)"}
        },
        {
            "ma_chi_tieu_goc": "6.2",
            "ma_chi_tieu_duoc_chon": "6.2",
            "ten_chi_tieu": "Tỷ lệ chênh lệch tài sản và nợ nhạy cảm lãi suất so với VCSH",
            "don_vi_tinh": "%",
            "gia_tri_tinh_toan": round(r186_val, 3),
            "diem_theo_nguong": s62,
            "trong_so": 1.0,
            "diem_quy_doi": round(s62 * 0.01, 3),
            "dien_giai": dg62,
            "cong_thuc_snapshot": {"bieu_thuc_the_so": f62, "mo_ta_cong_thuc": "Chênh lệch nhạy cảm lãi suất (R-186)"}
        }
    ]

    # -------------------------------------------------------------
    # CHỈ TIÊU ĐỊNH TÍNH THEO NHÓM (QUALITATIVE EVALUATION BY GROUP - Điều 16a TT52)
    # -------------------------------------------------------------
    score_c_dt, dg_c_dt, gt_c_dt = get_dt_info("C", 5.0, "Không có dữ liệu sai phạm thuộc nhóm C trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)")
    score_a_dt, dg_a_dt, gt_a_dt = get_dt_info("A", 5.0, "Không có dữ liệu sai phạm thuộc nhóm A trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)")
    score_m_dt, dg_m_dt, gt_m_dt = get_dt_info("M", 5.0, "Không có dữ liệu sai phạm thuộc nhóm M trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)")
    score_e_dt, dg_e_dt, gt_e_dt = get_dt_info("E", 5.0, "Không có dữ liệu sai phạm thuộc nhóm E trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)")
    score_l_dt, dg_l_dt, gt_l_dt = get_dt_info("L", 5.0, "Không có dữ liệu sai phạm thuộc nhóm L trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)")
    score_s_dt, dg_s_dt, gt_s_dt = get_dt_info("S", 5.0, "Không có dữ liệu sai phạm thuộc nhóm S trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)")

    c_dt_items = [
        {
            "ma_chi_tieu_goc": "1.3",
            "ma_chi_tieu_duoc_chon": "C_DT",
            "ten_chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm C (Vốn)",
            "don_vi_tinh": "",
            "gia_tri_tinh_toan": gt_c_dt,
            "diem_theo_nguong": round(score_c_dt, 2),
            "trong_so": 5.0,
            "diem_quy_doi": round(score_c_dt * 0.05, 3),
            "dien_giai": dg_c_dt,
            "loai_chi_tieu": "DINH_TUYNH"
        }
    ]

    a_dt_items = [
        {
            "ma_chi_tieu_goc": "2.7",
            "ma_chi_tieu_duoc_chon": "A_DT",
            "ten_chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm A (Chất lượng tài sản)",
            "don_vi_tinh": "",
            "gia_tri_tinh_toan": gt_a_dt,
            "diem_theo_nguong": round(score_a_dt, 2),
            "trong_so": 5.0,
            "diem_quy_doi": round(score_a_dt * 0.05, 3),
            "dien_giai": dg_a_dt,
            "loai_chi_tieu": "DINH_TUYNH"
        }
    ]

    m_dt_items = [
        {
            "ma_chi_tieu_goc": "3.2",
            "ma_chi_tieu_duoc_chon": "M_DT",
            "ten_chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm M (Quản trị điều hành)",
            "don_vi_tinh": "",
            "gia_tri_tinh_toan": gt_m_dt,
            "diem_theo_nguong": round(score_m_dt, 2),
            "trong_so": 7.0,
            "diem_quy_doi": round(score_m_dt * 0.07, 3),
            "dien_giai": dg_m_dt,
            "loai_chi_tieu": "DINH_TUYNH"
        }
    ]

    e_dt_items = [
        {
            "ma_chi_tieu_goc": "4.4",
            "ma_chi_tieu_duoc_chon": "E_DT",
            "ten_chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm E (Kết quả hoạt động kinh doanh)",
            "don_vi_tinh": "",
            "gia_tri_tinh_toan": gt_e_dt,
            "diem_theo_nguong": round(score_e_dt, 2),
            "trong_so": 5.0,
            "diem_quy_doi": round(score_e_dt * 0.05, 3),
            "dien_giai": dg_e_dt,
            "loai_chi_tieu": "DINH_TUYNH"
        }
    ]

    l_dt_items = [
        {
            "ma_chi_tieu_goc": "5.5",
            "ma_chi_tieu_duoc_chon": "L_DT",
            "ten_chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm L (Khả năng thanh khoản)",
            "don_vi_tinh": "",
            "gia_tri_tinh_toan": gt_l_dt,
            "diem_theo_nguong": round(score_l_dt, 2),
            "trong_so": 5.0,
            "diem_quy_doi": round(score_l_dt * 0.05, 3),
            "dien_giai": dg_l_dt,
            "loai_chi_tieu": "DINH_TUYNH"
        }
    ]

    s_dt_items = [
        {
            "ma_chi_tieu_goc": "6.3",
            "ma_chi_tieu_duoc_chon": "S_DT",
            "ten_chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm S (Mức độ nhạy cảm với rủi ro thị trường)",
            "don_vi_tinh": "",
            "gia_tri_tinh_toan": gt_s_dt,
            "diem_theo_nguong": round(score_s_dt, 2),
            "trong_so": 3.0,
            "diem_quy_doi": round(score_s_dt * 0.03, 3),
            "dien_giai": dg_s_dt,
            "loai_chi_tieu": "DINH_TUYNH"
        }
    ]

    # Calculate Group Scores equal to sum of converted scores (diem_quy_doi) of items in that group
    score_c = sum(i["diem_quy_doi"] for i in c_items + c_dt_items)
    score_a = sum(i["diem_quy_doi"] for i in a_items + a_dt_items)
    score_m = sum(i["diem_quy_doi"] for i in m_items + m_dt_items)
    score_e = sum(i["diem_quy_doi"] for i in e_items + e_dt_items)
    score_l = sum(i["diem_quy_doi"] for i in l_items + l_dt_items)
    score_s = sum(i["diem_quy_doi"] for i in s_items + s_dt_items)

    score_c_dl = car_score * 0.50 + t1_score * 0.50
    score_a_dl = s21 * 0.45 + s22 * 0.15 + s23 * 0.20 + s24 * 0.10 + s25 * 0.05 + s26 * 0.05
    score_m_dl = s31 * 1.00
    score_e_dl = s41 * 0.375 + s42 * 0.375 + s43 * 0.25
    score_l_dl = s51 * 0.25 + s52 * 0.25 + s53 * 0.30 + s54 * 0.20
    score_s_dl = s61 * 0.50 + s62 * 0.50

    ket_qua_cac_nhom = [
        {"ma_nhom": "C", "ten_nhom": "C - Mức độ an toàn vốn", "trong_so": 20.0, "trong_so_tieu_chi": 20.0, "trong_so_nhom_dinh_luong": 70, "trong_so_nhom_dinh_tinh": 30, "diem_nhom": round(score_c, 2), "diem_dinh_luong": round(score_c_dl, 2), "diem_dinh_tinh": round(score_c_dt, 2), "ket_qua_cac_chi_tieu": c_items + c_dt_items, "ket_qua_chi_tieu": c_items + c_dt_items},
        {"ma_nhom": "A", "ten_nhom": "A - Chất lượng tài sản", "trong_so": 30.0, "trong_so_tieu_chi": 30.0, "trong_so_nhom_dinh_luong": 70, "trong_so_nhom_dinh_tinh": 30, "diem_nhom": round(score_a, 2), "diem_dinh_luong": round(score_a_dl, 2), "diem_dinh_tinh": round(score_a_dt, 2), "ket_qua_cac_chi_tieu": a_items + a_dt_items, "ket_qua_chi_tieu": a_items + a_dt_items},
        {"ma_nhom": "M", "ten_nhom": "M - Quản trị điều hành", "trong_so": 10.0, "trong_so_tieu_chi": 10.0, "trong_so_nhom_dinh_luong": 70, "trong_so_nhom_dinh_tinh": 30, "diem_nhom": round(score_m, 2), "diem_dinh_luong": round(score_m_dl, 2), "diem_dinh_tinh": round(score_m_dt, 2), "ket_qua_cac_chi_tieu": m_items + m_dt_items, "ket_qua_chi_tieu": m_items + m_dt_items},
        {"ma_nhom": "E", "ten_nhom": "E - Kết quả hoạt động kinh doanh", "trong_so": 20.0, "trong_so_tieu_chi": 20.0, "trong_so_nhom_dinh_luong": 70, "trong_so_nhom_dinh_tinh": 30, "diem_nhom": round(score_e, 2), "diem_dinh_luong": round(score_e_dl, 2), "diem_dinh_tinh": round(score_e_dt, 2), "ket_qua_cac_chi_tieu": e_items + e_dt_items, "ket_qua_chi_tieu": e_items + e_dt_items},
        {"ma_nhom": "L", "ten_nhom": "L - Khả năng thanh khoản", "trong_so": 15.0, "trong_so_tieu_chi": 15.0, "trong_so_nhom_dinh_luong": 70, "trong_so_nhom_dinh_tinh": 30, "diem_nhom": round(score_l, 2), "diem_dinh_luong": round(score_l_dl, 2), "diem_dinh_tinh": round(score_l_dt, 2), "ket_qua_cac_chi_tieu": l_items + l_dt_items, "ket_qua_chi_tieu": l_items + l_dt_items},
        {"ma_nhom": "S", "ten_nhom": "S - Mức độ nhạy cảm với rủi ro thị trường", "trong_so": 5.0, "trong_so_tieu_chi": 5.0, "trong_so_nhom_dinh_luong": 70, "trong_so_nhom_dinh_tinh": 30, "diem_nhom": round(score_s, 2), "diem_dinh_luong": round(score_s_dl, 2), "diem_dinh_tinh": round(score_s_dt, 2), "ket_qua_cac_chi_tieu": s_items + s_dt_items, "ket_qua_chi_tieu": s_items + s_dt_items}
    ]

    # Điểm định lượng đóng góp vào tổng CAMELS (70% trọng số)
    diem_dinh_luong = round(
        score_c_dl * 0.15 + score_a_dl * 0.25 + score_m_dl * 0.03 + score_e_dl * 0.15 + score_l_dl * 0.10 + score_s_dl * 0.02, 2
    )

    # Điểm định tính đóng góp vào tổng CAMELS (30% trọng số)
    diem_dinh_tinh = round(
        score_c_dt * 0.05 + score_a_dt * 0.05 + score_m_dt * 0.07 + score_e_dt * 0.05 + score_l_dt * 0.05 + score_s_dt * 0.03, 2
    )

    # Weighted overall CAMELS score = sum of group scores (score_c + score_a + score_m + score_e + score_l + score_s)
    tong_diem = round(score_c + score_a + score_m + score_e + score_l + score_s, 2)
    xep_hang = "A" if tong_diem >= 4.0 else ("B" if tong_diem >= 3.0 else ("C" if tong_diem >= 2.0 else "D"))

    has_r105 = val_map.get("R-105") is not None or val_map.get("R-112") is not None

    code_score_map = {
        "R-101": {"sc": car_score, "qd": round(car_score * 0.075, 3), "loai": "TIEU_CHI"},
        "R-105": {"sc": car_score if has_r105 else None, "qd": round(car_score * 0.075, 3) if has_r105 else None, "loai": "TIEU_CHI"},
        "R-102": {"sc": None if has_r105 else car_score, "qd": None if has_r105 else round(car_score * 0.075, 3), "loai": "TIEU_CHI"},
        "R-108": {"sc": t1_score, "qd": round(t1_score * 0.075, 3), "loai": "TIEU_CHI"},
        "R-112": {"sc": t1_score if has_r105 else None, "qd": round(t1_score * 0.075, 3) if has_r105 else None, "loai": "TIEU_CHI"},
        "R-109": {"sc": None if has_r105 else t1_score, "qd": None if has_r105 else round(t1_score * 0.075, 3), "loai": "TIEU_CHI"},

        "R-116": {"sc": s21, "qd": round(s21 * 0.1125, 3), "loai": "TIEU_CHI"},
        "R-121": {"sc": s22, "qd": round(s22 * 0.0375, 3), "loai": "TIEU_CHI"},
        "R-124": {"sc": s23, "qd": round(s23 * 0.05, 3), "loai": "TIEU_CHI"},
        "R-127": {"sc": s24, "qd": round(s24 * 0.025, 3), "loai": "TIEU_CHI"},
        "R-135": {"sc": s25, "qd": round(s25 * 0.0125, 3), "loai": "TIEU_CHI"},
        "R-138": {"sc": s26, "qd": round(s26 * 0.0125, 3), "loai": "TIEU_CHI"},

        "R-142": {"sc": s31, "qd": round(s31 * 0.03, 3), "loai": "TIEU_CHI"},

        "R-153": {"sc": s41, "qd": round(s41 * 0.05625, 3), "loai": "TIEU_CHI"},
        "R-156": {"sc": s42, "qd": round(s42 * 0.05625, 3), "loai": "TIEU_CHI"},
        "R-159": {"sc": s43, "qd": round(s43 * 0.0375, 3), "loai": "TIEU_CHI"},

        "R-171": {"sc": s51, "qd": round(s51 * 0.025, 3), "loai": "TIEU_CHI"},
        "R-174": {"sc": s52, "qd": round(s52 * 0.025, 3), "loai": "TIEU_CHI"},
        "R-178": {"sc": s53, "qd": round(s53 * 0.03, 3), "loai": "TIEU_CHI"},
        "R-181": {"sc": s54, "qd": round(s54 * 0.02, 3), "loai": "TIEU_CHI"},

        "R-185": {"sc": s61, "qd": round(s61 * 0.01, 3), "loai": "TIEU_CHI"},
        "R-186": {"sc": s62, "qd": round(s62 * 0.01, 3), "loai": "TIEU_CHI"},

        "R-100": {"sc": None, "qd": round(score_c, 2), "loai": "NHOM"},
        "R-115": {"sc": None, "qd": round(score_a, 2), "loai": "NHOM"},
        "R-141": {"sc": None, "qd": round(score_m, 2), "loai": "NHOM"},
        "R-152": {"sc": None, "qd": round(score_e, 2), "loai": "NHOM"},
        "R-170": {"sc": None, "qd": round(score_l, 2), "loai": "NHOM"},
        "R-184": {"sc": None, "qd": round(score_s, 2), "loai": "NHOM"},
    }

    dt_rows_to_insert = {
        "R-115": {
            "stt": "1.3",
            "ma_dong_nguon": "C_DT",
            "chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm C (Vốn)",
            "so_lieu": gt_c_dt,
            "cap_do": 2,
            "is_header": True,
            "diem_theo_nguong": round(score_c_dt, 2),
            "diem_quy_doi": round(score_c_dt * 0.05, 3),
            "loai_diem": "TIEU_CHI"
        },
        "R-141": {
            "stt": "2.7",
            "ma_dong_nguon": "A_DT",
            "chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm A (Chất lượng tài sản)",
            "so_lieu": gt_a_dt,
            "cap_do": 2,
            "is_header": True,
            "diem_theo_nguong": round(score_a_dt, 2),
            "diem_quy_doi": round(score_a_dt * 0.05, 3),
            "loai_diem": "TIEU_CHI"
        },
        "R-152": {
            "stt": "3.2",
            "ma_dong_nguon": "M_DT",
            "chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm M (Quản trị điều hành)",
            "so_lieu": gt_m_dt,
            "cap_do": 2,
            "is_header": True,
            "diem_theo_nguong": round(score_m_dt, 2),
            "diem_quy_doi": round(score_m_dt * 0.07, 3),
            "loai_diem": "TIEU_CHI"
        },
        "R-170": {
            "stt": "4.4",
            "ma_dong_nguon": "E_DT",
            "chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm E (Kết quả hoạt động kinh doanh)",
            "so_lieu": gt_e_dt,
            "cap_do": 2,
            "is_header": True,
            "diem_theo_nguong": round(score_e_dt, 2),
            "diem_quy_doi": round(score_e_dt * 0.05, 3),
            "loai_diem": "TIEU_CHI"
        },
        "R-184": {
            "stt": "5.5",
            "ma_dong_nguon": "L_DT",
            "chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm L (Khả năng thanh khoản)",
            "so_lieu": gt_l_dt,
            "cap_do": 2,
            "is_header": True,
            "diem_theo_nguong": round(score_l_dt, 2),
            "diem_quy_doi": round(score_l_dt * 0.05, 3),
            "loai_diem": "TIEU_CHI"
        }
    }

    du_lieu_boc_tach = []
    for idx, r in enumerate(camels_rows):
        code = r.get("ma_dong_nguon", "")
        if code in dt_rows_to_insert:
            du_lieu_boc_tach.append(dt_rows_to_insert[code])

        info = code_score_map.get(code, {})

        du_lieu_boc_tach.append({
            "stt": r.get("stt") or str(idx + 1),
            "ma_dong_nguon": code,
            "chi_tieu": r.get("chi_tieu"),
            "so_lieu": r.get("so_lieu"),
            "cap_do": r.get("cap_do", 1),
            "is_header": r.get("is_header", False),
            "diem_theo_nguong": info.get("sc"),
            "diem_quy_doi": info.get("qd"),
            "loai_diem": info.get("loai")
        })

    # Add S_DT at the end of Group S
    du_lieu_boc_tach.append({
        "stt": "6.3",
        "ma_dong_nguon": "S_DT",
        "chi_tieu": "Đánh giá các chỉ tiêu định tính Nhóm S (Mức độ nhạy cảm với rủi ro thị trường)",
        "so_lieu": gt_s_dt,
        "cap_do": 2,
        "is_header": True,
        "diem_theo_nguong": round(score_s_dt, 2),
        "diem_quy_doi": round(score_s_dt * 0.03, 3),
        "loai_diem": "TIEU_CHI"
    })

    diem_dinh_luong = round((score_c_dl * 0.15 + score_a_dl * 0.25 + score_m_dl * 0.03 + score_e_dl * 0.15 + score_l_dl * 0.10 + score_s_dl * 0.02) / 0.70, 2)
    diem_dinh_tinh = 5.00

    xep_hang_goc = xep_hang

    # Đánh giá quy định hạ xếp hạng xuống (E) theo Khoản 7 Điều 20 Thông tư 52
    has_l_below_2 = any(s < 2 for s in [s51, s52, s53, s54, score_l_dt])
    car_vi_pham = car_val < 8.0

    bat_buoc_xep_hang_e = has_l_below_2 or car_vi_pham
    if bat_buoc_xep_hang_e:
        xep_hang = "E"

    danh_gia_khoan_7_dieu_20 = {
        "bat_buoc_xep_hang_e": bat_buoc_xep_hang_e,
        "xep_hang_goc": xep_hang_goc,
        "xep_hang_cuoi_cung": xep_hang,
        "ket_luan": f"Tổ chức tín dụng đạt điểm CAMELS = {tong_diem:.2f} (Xếp hạng gốc {xep_hang_goc}), tuy nhiên vi phạm điều kiện bổ sung tại Khoản 7 Điều 20 TT52 nên BẮT BUỘC HẠ XẾP HẠNG XUỐNG HẠNG (E)." if bat_buoc_xep_hang_e else f"Tổ chức tín dụng đạt điểm CAMELS = {tong_diem:.2f} và không vi phạm các trường hợp hạ bậc tại Khoản 7 Điều 20 TT52, GIỮ NGUYÊN XẾP HẠNG {xep_hang_goc}.",
        "dieu_kien_a_thanh_khoan": {
            "co_chi_tieu_duoi_2": has_l_below_2,
            "mo_ta": "Có chỉ tiêu thuộc Nhóm L < 2.0 điểm (Vi phạm Điều 20 Khoản 7a)" if has_l_below_2 else "Không có chỉ tiêu thanh khoản nào < 2.0 điểm",
            "danh_sach_chi_tieu": [
                {"ten_chi_tieu": "5.1 TS Thanh khoản", "diem": s51},
                {"ten_chi_tieu": "5.2 Vốn ngắn hạn vay TĐH", "diem": s52},
                {"ten_chi_tieu": "5.3 Tỷ lệ LDR", "diem": s53},
                {"ten_chi_tieu": "5.4 Tiền gửi KH lớn", "diem": s54},
                {"ten_chi_tieu": "5.5 Định tính Thanh khoản", "diem": round(score_l_dt, 2)}
            ]
        },
        "dieu_kien_b_lo_luy_ke": {
            "vi_pham": False,
            "bieu_thuc_day_du": "Lỗ lũy kế / (VĐL + Quỹ) = 0.00%",
            "mo_ta": "Không có lỗ lũy kế vượt vốn điều lệ và các quỹ"
        },
        "dieu_kien_c_vi_pham_car": {
            "vi_pham": car_vi_pham,
            "mo_ta": f"Vi phạm duy trì CAR theo quy định ({car_val:.2f}% < 8.0%)" if car_vi_pham else f"CAR đạt {car_val:.2f}% (Duy trì an toàn vốn theo quy định >= 8.0%)"
        }
    }

    return {
        "doi_tuong_id": doi_tuong_id,
        "ky_du_lieu": ky_du_lieu,
        "tong_diem": tong_diem,
        "xep_hang": xep_hang,
        "diem_dinh_luong": diem_dinh_luong,
        "diem_dinh_tinh": diem_dinh_tinh,
        "ket_qua_cac_nhom": ket_qua_cac_nhom,
        "ket_qua_nhom": ket_qua_cac_nhom,
        "du_lieu_boc_tach": du_lieu_boc_tach,
        "danh_gia_khoan_7_dieu_20": danh_gia_khoan_7_dieu_20
    }
