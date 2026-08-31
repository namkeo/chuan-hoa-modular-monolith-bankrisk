from typing import Dict, Any, Optional

class DieuKienService:
    """
    Engine kiểm tra điều kiện áp dụng cho chỉ tiêu.
    """

    @staticmethod
    def kiem_tra_dieu_kien(dieu_kien: Optional[Dict[str, Any]], thuoc_tinh: Dict[str, Any]) -> bool:
        if not dieu_kien:
            return True

        kieu = dieu_kien.get("kieu", "LUON_DUNG")
        if kieu == "LUON_DUNG":
            return True

        if kieu == "SO_SANH":
            truong = dieu_kien.get("truong")
            if not truong:
                return True

            val = thuoc_tinh.get(truong)
            target = dieu_kien.get("gia_tri")
            op = dieu_kien.get("phep_so_sanh", "BANG")

            if op == "BANG":
                return val == target
            elif op == "KHAC":
                return val != target
            elif op == "LON_HON":
                return val is not None and val > target
            elif op == "LON_HON_HOAC_BANG":
                return val is not None and val >= target
            elif op == "NHO_HON":
                return val is not None and val < target
            elif op == "NHO_HON_HOAC_BANG":
                return val is not None and val <= target
            elif op == "TRONG_DANH_SACH":
                return isinstance(target, (list, tuple, set)) and val in target
            elif op == "KHONG_TRONG_DANH_SACH":
                return isinstance(target, (list, tuple, set)) and val not in target
            else:
                return False

        return True
