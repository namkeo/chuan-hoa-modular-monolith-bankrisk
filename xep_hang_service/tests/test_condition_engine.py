from app.services.dieu_kien_service import DieuKienService

def test_condition_tt41():
    """
    Test chọn chỉ tiêu thay thế dựa trên điều kiện ap_dung_thong_tu_41
    """
    dk_1_1 = {
        "kieu": "SO_SANH",
        "truong": "ap_dung_thong_tu_41",
        "phep_so_sanh": "BANG",
        "gia_tri": False
    }

    dk_1_1_a = {
        "kieu": "SO_SANH",
        "truong": "ap_dung_thong_tu_41",
        "phep_so_sanh": "BANG",
        "gia_tri": True
    }

    thuoc_tinh_true = {"ap_dung_thong_tu_41": True}
    assert DieuKienService.kiem_tra_dieu_kien(dk_1_1, thuoc_tinh_true) is False
    assert DieuKienService.kiem_tra_dieu_kien(dk_1_1_a, thuoc_tinh_true) is True

    thuoc_tinh_false = {"ap_dung_thong_tu_41": False}
    assert DieuKienService.kiem_tra_dieu_kien(dk_1_1, thuoc_tinh_false) is True
    assert DieuKienService.kiem_tra_dieu_kien(dk_1_1_a, thuoc_tinh_false) is False
