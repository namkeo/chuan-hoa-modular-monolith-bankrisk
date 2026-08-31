from decimal import Decimal
from typing import Dict, Any, List, Optional
from app.utils.decimal_utils import to_decimal

class KiemTraCauHinhService:
    """
    Service kiểm tra tính hợp lệ của cấu hình Bộ tiêu chí / Chỉ tiêu trước khi công bố.
    """

    @classmethod
    def kiem_tra_cong_thuc(cls, cong_thuc: Dict[str, Any], danh_sach_bien: List[Dict[str, Any]]) -> List[str]:
        errors = []
        danh_sach_ma_bien = {b.get("ma_bien") for b in danh_sach_bien if isinstance(b, dict) and b.get("ma_bien")}

        def _traverse(node: Any):
            if not isinstance(node, dict) or not node:
                errors.append("Nút công thức rỗng hoặc không phải object")
                return

            if "gia_tri" in node:
                if node["gia_tri"] is None:
                    errors.append("Hằng số trong công thức không được null")
                return

            if "ma_bien" in node:
                ma_bien = node["ma_bien"]
                if ma_bien not in danh_sach_ma_bien:
                    errors.append(f"Biến '{ma_bien}' trong công thức chưa được khai báo trong danh_sach_bien")
                return

            if "phep_toan" in node:
                op = node["phep_toan"]
                params = node.get("tham_so", [])
                supported = ["CONG", "TRU", "NHAN", "CHIA", "MIN", "MAX", "TRUNG_BINH", "LUY_THUA", "GIA_TRI_TUYET_DOI"]
                if op not in supported:
                    errors.append(f"Phép toán '{op}' không nằm trong danh sách hỗ trợ")

                if op == "CHIA" and len(params) != 2:
                    errors.append("Phép CHIA phải có đúng 2 tham số")
                elif op in ["CONG", "NHAN"] and len(params) < 2:
                    errors.append(f"Phép {op} phải có tối thiểu 2 tham số")

                for p in params:
                    _traverse(p)
                return

            errors.append(f"Cấu trúc nút công thức không hợp lệ: {node}")

        _traverse(cong_thuc)
        return errors

    @classmethod
    def kiem_tra_nguong_diem(cls, cac_muc_diem: List[Dict[str, Any]]) -> List[str]:
        errors = []
        if not cac_muc_diem:
            return ["Danh sách mức điểm rỗng"]

        for idx, muc in enumerate(cac_muc_diem):
            diem = muc.get("diem")
            if diem is not None and diem > 5.0:
                errors.append(f"Mức điểm {diem} ở phần tử {idx+1} vượt quá điểm tối đa (5.0)")

        # Kiểm tra trùng lặp hoàn toàn
        for i in range(len(cac_muc_diem)):
            for j in range(i + 1, len(cac_muc_diem)):
                m1, m2 = cac_muc_diem[i], cac_muc_diem[j]
                if (m1.get("diem") == m2.get("diem") and
                    m1.get("tu") == m2.get("tu") and
                    m1.get("den") == m2.get("den") and
                    m1.get("bao_gom_tu") == m2.get("bao_gom_tu") and
                    m1.get("bao_gom_den") == m2.get("bao_gom_den")):
                    errors.append(f"Phần tử mức điểm {i+1} và {j+1} hoàn toàn giống nhau")

        return errors

    @classmethod
    def kiem_tra_tong_trong_so(
        cls,
        danh_sach_chi_tieu: List[Dict[str, Any]],
        ma_loai_doi_tuong: str
    ) -> List[str]:
        """
        Kiểm tra tổng trọng số các chỉ tiêu theo từng nhóm tiêu chí cho loại đối tượng = 100%.
        """
        errors = []
        nhom_weights: Dict[str, Decimal] = {}

        for ct in danh_sach_chi_tieu:
            nhom_id = ct.get("nhom_tieu_chi_id", "UNKNOWN")
            cau_hinh = ct.get("cau_hinh_theo_doi_tuong", [])
            matched = [c for c in cau_hinh if c.get("ma_loai_doi_tuong") == ma_loai_doi_tuong]
            if matched:
                trong_so = to_decimal(matched[0].get("trong_so", 0))
                nhom_weights[nhom_id] = nhom_weights.get(nhom_id, Decimal("0")) + trong_so

        tolerance = Decimal("0.0001")
        for nhom_id, tong in nhom_weights.items():
            if abs(tong - Decimal("100")) > tolerance:
                errors.append(
                    f"Nhóm tiêu chí '{nhom_id}' có tổng trọng số cho loại đối tượng '{ma_loai_doi_tuong}' là {tong}%, khác 100%"
                )

        return errors
