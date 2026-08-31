import pytest
from decimal import Decimal
from app.services.cong_thuc_service import CongThucService
from app.core.exceptions import DivisionByZeroException, MissingInputDataException

def test_formula_ratio_npl():
    """
    Test công thức Nợ nhóm 2 / Tổng nợ * 100
    NO_NHOM_2 = 1280, TONG_NO = 40000 -> 3.2
    """
    formula = {
        "phep_toan": "NHAN",
        "tham_so": [
            {
                "phep_toan": "CHIA",
                "tham_so": [
                    {"ma_bien": "NO_NHOM_2"},
                    {"ma_bien": "TONG_NO"}
                ]
            },
            {"gia_tri": 100}
        ]
    }
    data = {"NO_NHOM_2": 1280, "TONG_NO": 40000}
    res = CongThucService.tinh_bieu_thuc(formula, data, ma_chi_tieu="2.2")
    assert res == Decimal("3.2")

def test_formula_car_tt41():
    """
    Test công thức CAR TT41: C / [RWA + 12.5 * (KOR + KMR)] * 100
    C=10000, RWA=90000, KOR=100, KMR=50
    Denominator = 90000 + 12.5 * 150 = 91875
    Result = 10000 / 91875 * 100 = 10.88435374...
    """
    formula = {
        "phep_toan": "NHAN",
        "tham_so": [
            {
                "phep_toan": "CHIA",
                "tham_so": [
                    {"ma_bien": "C"},
                    {
                        "phep_toan": "CONG",
                        "tham_so": [
                            {"ma_bien": "RWA"},
                            {
                                "phep_toan": "NHAN",
                                "tham_so": [
                                    {"gia_tri": 12.5},
                                    {
                                        "phep_toan": "CONG",
                                        "tham_so": [
                                            {"ma_bien": "KOR"},
                                            {"ma_bien": "KMR"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            {"gia_tri": 100}
        ]
    }
    data = {"C": 10000, "RWA": 90000, "KOR": 100, "KMR": 50}
    res = CongThucService.tinh_bieu_thuc(formula, data, ma_chi_tieu="1.1.a")
    assert round(float(res), 4) == 10.8844

def test_formula_division_by_zero():
    """
    Test mẫu số bằng 0 -> bắn ra DivisionByZeroException
    """
    formula = {
        "phep_toan": "CHIA",
        "tham_so": [
            {"ma_bien": "NO_NHOM_2"},
            {"ma_bien": "TONG_NO"}
        ]
    }
    data = {"NO_NHOM_2": 1280, "TONG_NO": 0}
    with pytest.raises(DivisionByZeroException) as exc_info:
        CongThucService.tinh_bieu_thuc(formula, data, ma_chi_tieu="2.2")
    assert exc_info.value.detail["ma_loi"] == "CHIA_CHO_0"

def test_formula_missing_variable():
    """
    Test thiếu biến bắt buộc -> MissingInputDataException
    """
    formula = {
        "phep_toan": "CHIA",
        "tham_so": [
            {"ma_bien": "NO_NHOM_2"},
            {"ma_bien": "TONG_NO"}
        ]
    }
    data = {"NO_NHOM_2": 1280}
    with pytest.raises(MissingInputDataException) as exc_info:
        CongThucService.tinh_bieu_thuc(formula, data, ma_chi_tieu="2.2")
    assert exc_info.value.detail["ma_loi"] == "THIEU_DU_LIEU_DAU_VAO"
    assert "TONG_NO" in exc_info.value.detail["danh_sach_bien_thieu"]
