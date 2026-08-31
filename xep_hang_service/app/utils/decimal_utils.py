from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional

def to_decimal(val: Any) -> Optional[Decimal]:
    """
    Chuyển đổi an toàn giá trị bất kỳ sang Decimal.
    """
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, str)):
        return Decimal(str(val))
    if isinstance(val, float):
        return Decimal(str(val))
    try:
        return Decimal(str(val))
    except Exception:
        raise ValueError(f"Không thể chuyển đổi giá trị '{val}' sang Decimal")

def round_decimal(val: Decimal, decimal_places: int = 4) -> Decimal:
    """
    Làm tròn Decimal theo số chữ số thập phân (mặc định 4 chữ số).
    """
    if val is None:
        return None
    pattern = Decimal('1.' + '0' * decimal_places) if decimal_places > 0 else Decimal('1')
    return val.quantize(pattern, rounding=ROUND_HALF_UP)

def decimal_to_float_or_int(val: Any) -> Any:
    """
    Chuyển Decimal sang float/int hoặc giữ nguyên để serialize JSON.
    """
    if isinstance(val, Decimal):
        if val % 1 == 0:
            return int(val)
        return float(val)
    if isinstance(val, dict):
        return {k: decimal_to_float_or_int(v) for k, v in val.items()}
    if isinstance(val, list):
        return [decimal_to_float_or_int(v) for v in val]
    return val
