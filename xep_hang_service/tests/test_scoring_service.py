from decimal import Decimal
from app.utils.decimal_utils import round_decimal

def test_converted_score_calculation():
    """
    Test tính điểm quy đổi:
    Điểm theo ngưỡng = 4
    Trọng số = 15%
    Điểm quy đổi = 4 * 15 / 100 = 0.60
    """
    diem_theo_nguong = Decimal("4")
    trong_so = Decimal("15")

    diem_quy_doi = (diem_theo_nguong * trong_so) / Decimal("100")
    assert round_decimal(diem_quy_doi, 2) == Decimal("0.60")
