from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Any, Dict, List, Optional

class BaseScoringException(HTTPException):
    def __init__(
        self,
        status_code: int,
        ma_loi: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        detail = {
            "ma_loi": ma_loi,
            "message": message
        }
        if extra:
            detail.update(extra)
        super().__init__(status_code=status_code, detail=detail)

class MissingInputDataException(BaseScoringException):
    def __init__(self, missing_vars: List[str], message: str = "Thiếu dữ liệu đầu vào để tính điểm"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            ma_loi="THIEU_DU_LIEU_DAU_VAO",
            message=message,
            extra={"danh_sach_bien_thieu": missing_vars}
        )

class DivisionByZeroException(BaseScoringException):
    def __init__(self, ma_chi_tieu: str, message: str = "Không thể tính chỉ tiêu do mẫu số bằng 0"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            ma_loi="CHIA_CHO_0",
            message=message,
            extra={"ma_chi_tieu": ma_chi_tieu}
        )

class ThresholdNotFoundException(BaseScoringException):
    def __init__(self, ma_chi_tieu: str, gia_tri: Any, message: str = "Không tìm thấy mức điểm phù hợp"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            ma_loi="KHONG_TIM_THAY_NGUONG",
            message=message,
            extra={"ma_chi_tieu": ma_chi_tieu, "gia_tri": gia_tri}
        )

class CriteriaConflictException(BaseScoringException):
    def __init__(self, ma_chi_tieu_goc: str, danh_sach_chi_tieu: List[str], message: str = "Có nhiều chỉ tiêu cùng thỏa mãn điều kiện áp dụng"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            ma_loi="XUNG_DOT_PHUONG_AN",
            message=message,
            extra={"ma_chi_tieu_goc": ma_chi_tieu_goc, "danh_sach_chi_tieu": danh_sach_chi_tieu}
        )

class ConfigurationException(BaseScoringException):
    def __init__(self, message: str, ma_loi: str = "LOI_CAU_HINH", extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            ma_loi=ma_loi,
            message=message,
            extra=extra
        )

class NotFoundException(BaseScoringException):
    def __init__(self, message: str = "Không tìm thấy dữ liệu"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            ma_loi="KHONG_TIM_THAY",
            message=message
        )
