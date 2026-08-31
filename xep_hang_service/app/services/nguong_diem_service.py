from decimal import Decimal
from typing import Dict, Any, List, Optional
from app.utils.decimal_utils import to_decimal
from app.core.exceptions import ThresholdNotFoundException, ConfigurationException

class NguongDiemService:
    """
    Engine tra mức điểm dựa trên các khoảng cấu hình.
    """

    @staticmethod
    def nam_trong_khoang(gia_tri: Decimal, muc_diem: Dict[str, Any]) -> bool:
        tu = muc_diem.get("tu")
        bao_gom_tu = muc_diem.get("bao_gom_tu", False)
        den = muc_diem.get("den")
        bao_gom_den = muc_diem.get("bao_gom_den", False)

        # Kiểm tra giới hạn dưới (từ)
        if tu is not None:
            tu_dec = to_decimal(tu)
            if bao_gom_tu:
                if not (gia_tri >= tu_dec):
                    return False
            else:
                if not (gia_tri > tu_dec):
                    return False

        # Kiểm tra giới hạn trên (đến)
        if den is not None:
            den_dec = to_decimal(den)
            if bao_gom_den:
                if not (gia_tri <= den_dec):
                    return False
            else:
                if not (gia_tri < den_dec):
                    return False

        return True

    @classmethod
    def tim_muc_diem(
        cls,
        gia_tri: Decimal,
        cac_muc_diem: List[Dict[str, Any]],
        ma_chi_tieu: str = ""
    ) -> Dict[str, Any]:
        if not cac_muc_diem:
            raise ThresholdNotFoundException(ma_chi_tieu=ma_chi_tieu, gia_tri=float(gia_tri))

        phu_hop: List[Dict[str, Any]] = []
        for muc in cac_muc_diem:
            if cls.nam_trong_khoang(gia_tri, muc):
                phu_hop.append(muc)

        if len(phu_hop) == 0:
            raise ThresholdNotFoundException(ma_chi_tieu=ma_chi_tieu, gia_tri=float(gia_tri))

        if len(phu_hop) > 1:
            raise ConfigurationException(
                message=f"Giá trị {gia_tri} của chỉ tiêu '{ma_chi_tieu}' khớp với {len(phu_hop)} mức điểm (chồng lấn ngưỡng)",
                ma_loi="CHONG_LAN_NGUONG",
                extra={"ma_chi_tieu": ma_chi_tieu, "gia_tri": float(gia_tri), "cac_muc_trung": phu_hop}
            )

        return phu_hop[0]

    @staticmethod
    def tao_dien_giai(gia_tri: Decimal, muc_diem: Dict[str, Any]) -> str:
        diem = muc_diem.get("diem")
        tu = muc_diem.get("tu")
        bao_gom_tu = muc_diem.get("bao_gom_tu", False)
        den = muc_diem.get("den")
        bao_gom_den = muc_diem.get("bao_gom_den", False)

        fv = float(gia_tri)
        if fv.is_integer():
            str_val = str(int(fv))
        else:
            str_val = f"{fv:.3f}".replace(".", ",")

        if tu is None and den is not None:
            operator = "<=" if bao_gom_den else "<"
            return f"Giá trị {str_val} {operator} {den} nên được {diem} điểm"
        elif tu is not None and den is None:
            operator = ">=" if bao_gom_tu else ">"
            return f"Giá trị {str_val} {operator} {tu} nên được {diem} điểm"
        elif tu is not None and den is not None:
            op_tu = "lớn hơn hoặc bằng" if bao_gom_tu else "lớn hơn"
            op_den = "nhỏ hơn hoặc bằng" if bao_gom_den else "nhỏ hơn"
            return f"Giá trị {str_val} {op_tu} {tu} và {op_den} {den} nên được {diem} điểm"
        else:
            return f"Giá trị {str_val} được {diem} điểm"
