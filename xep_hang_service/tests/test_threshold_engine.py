import pytest
from decimal import Decimal
from app.services.nguong_diem_service import NguongDiemService

def test_threshold_cang_nho_cang_tot():
    """
    Test CÀNG NHỎ CÀNG TỐT:
    Giá trị = 3.2
    Ngưỡng:
    <= 2.5     -> 5 điểm
    > 2.5 <= 4 -> 4 điểm
    > 4 <= 5.5 -> 3 điểm
    > 5.5 <= 7 -> 2 điểm
    > 7        -> 1 điểm
    Kết quả: 4 điểm
    """
    cac_muc_diem = [
        {"diem": 5, "tu": None, "bao_gom_tu": False, "den": 2.5, "bao_gom_den": True},
        {"diem": 4, "tu": 2.5, "bao_gom_tu": False, "den": 4, "bao_gom_den": True},
        {"diem": 3, "tu": 4, "bao_gom_tu": False, "den": 5.5, "bao_gom_den": True},
        {"diem": 2, "tu": 5.5, "bao_gom_tu": False, "den": 7, "bao_gom_den": True},
        {"diem": 1, "tu": 7, "bao_gom_tu": False, "den": None, "bao_gom_den": False}
    ]
    val = Decimal("3.2")
    matched = NguongDiemService.tim_muc_diem(val, cac_muc_diem, ma_chi_tieu="2.2")
    assert matched["diem"] == 4

def test_threshold_cang_lon_cang_tot():
    """
    Test CÀNG LỚN CÀNG TỐT:
    Giá trị = 13
    Ngưỡng:
    >= 15 -> 5
    >= 12 -> 4
    >= 8  -> 3
    >= 5  -> 2
    < 5   -> 1
    Kết quả: 4 điểm
    """
    cac_muc_diem = [
        {"diem": 5, "tu": 15, "bao_gom_tu": True, "den": None, "bao_gom_den": False},
        {"diem": 4, "tu": 12, "bao_gom_tu": True, "den": 15, "bao_gom_den": False},
        {"diem": 3, "tu": 8, "bao_gom_tu": True, "den": 12, "bao_gom_den": False},
        {"diem": 2, "tu": 5, "bao_gom_tu": True, "den": 8, "bao_gom_den": False},
        {"diem": 1, "tu": None, "bao_gom_tu": False, "den": 5, "bao_gom_den": False}
    ]
    val = Decimal("13")
    matched = NguongDiemService.tim_muc_diem(val, cac_muc_diem, ma_chi_tieu="1.1.a")
    assert matched["diem"] == 4
