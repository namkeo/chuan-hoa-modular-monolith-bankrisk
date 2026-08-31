from decimal import Decimal, getcontext
import math
from typing import Dict, Any, List
from app.utils.decimal_utils import to_decimal
from app.core.exceptions import (
    MissingInputDataException,
    DivisionByZeroException,
    ConfigurationException
)

# Set high precision for Decimal calculations
getcontext().prec = 28

class CongThucService:
    """
    Engine tính toán công thức AST dựa trên Decimal.
    Không sử dụng eval() hoặc exec().
    """

    @classmethod
    def tinh_bieu_thuc(
        cls,
        node: Dict[str, Any],
        du_lieu: Dict[str, Any],
        ma_chi_tieu: str = ""
    ) -> Decimal:
        if not isinstance(node, dict):
            raise ConfigurationException(f"Nút công thức phải là dict, nhận được: {type(node)}")

        # 1. Nút Hằng Số
        if "gia_tri" in node:
            val = node["gia_tri"]
            if val is None:
                raise ConfigurationException("Hằng số trong công thức không được null")
            return to_decimal(val)

        # 2. Nút Biến
        if "ma_bien" in node:
            ma_bien = node["ma_bien"]
            if ma_bien not in du_lieu or du_lieu[ma_bien] is None:
                raise MissingInputDataException(missing_vars=[ma_bien])
            val = du_lieu[ma_bien]
            try:
                return to_decimal(val)
            except ValueError:
                raise ConfigurationException(f"Giá trị của biến '{ma_bien}' ({val}) không phải số hợp lệ")

        # 3. Nút Phép Toán
        if "phep_toan" in node:
            op = node["phep_toan"]
            params = node.get("tham_so", [])
            if not isinstance(params, list):
                raise ConfigurationException(f"Tham số của phép toán '{op}' phải là list")

            # Tính toán danh sách tham số con
            evaluated_params: List[Decimal] = [
                cls.tinh_bieu_thuc(p, du_lieu, ma_chi_tieu=ma_chi_tieu)
                for p in params
            ]

            if op == "CONG":
                if len(evaluated_params) < 2:
                    raise ConfigurationException("Phép CONG cần tối thiểu 2 tham số")
                res = evaluated_params[0]
                for p in evaluated_params[1:]:
                    res += p
                return res

            elif op == "TRU":
                if len(evaluated_params) == 1:
                    return -evaluated_params[0]
                elif len(evaluated_params) == 2:
                    return evaluated_params[0] - evaluated_params[1]
                else:
                    raise ConfigurationException("Phép TRU cần 1 hoặc 2 tham số")

            elif op == "NHAN":
                if len(evaluated_params) < 2:
                    raise ConfigurationException("Phép NHAN cần tối thiểu 2 tham số")
                res = evaluated_params[0]
                for p in evaluated_params[1:]:
                    res *= p
                return res

            elif op == "CHIA":
                if len(evaluated_params) != 2:
                    raise ConfigurationException("Phép CHIA cần chính xác 2 tham số")
                mau_so = evaluated_params[1]
                if mau_so == Decimal("0"):
                    raise DivisionByZeroException(ma_chi_tieu=ma_chi_tieu)
                return evaluated_params[0] / mau_so

            elif op == "MIN":
                if not evaluated_params:
                    raise ConfigurationException("Phép MIN cần ít nhất 1 tham số")
                return min(evaluated_params)

            elif op == "MAX":
                if not evaluated_params:
                    raise ConfigurationException("Phép MAX cần ít nhất 1 tham số")
                return max(evaluated_params)

            elif op == "TRUNG_BINH":
                if not evaluated_params:
                    raise ConfigurationException("Phép TRUNG_BINH cần ít nhất 1 tham số")
                return sum(evaluated_params) / Decimal(str(len(evaluated_params)))

            elif op == "LUY_THUA":
                if len(evaluated_params) != 2:
                    raise ConfigurationException("Phép LUY_THUA cần 2 tham số")
                try:
                    base = float(evaluated_params[0])
                    exp = float(evaluated_params[1])
                    return to_decimal(math.pow(base, exp))
                except Exception as e:
                    raise ConfigurationException(f"Lỗi tính lũy thừa: {e}")

            elif op == "GIA_TRI_TUYET_DOI":
                if len(evaluated_params) != 1:
                    raise ConfigurationException("Phép GIA_TRI_TUYET_DOI cần 1 tham số")
                return abs(evaluated_params[0])

            else:
                raise ConfigurationException(f"Toán tử '{op}' không được hỗ trợ")

        raise ConfigurationException(f"Cấu trúc nút công thức không hợp lệ: {node}")
