from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class DoiTuongDanhGiaBase(BaseModel):
    ma_doi_tuong: str
    ten_doi_tuong: str
    ma_loai_doi_tuong: str
    ten_loai_doi_tuong: Optional[str] = None
    thuoc_tinh: Dict[str, Any] = {}
    is_active: int = 1

class DoiTuongDanhGiaCreate(DoiTuongDanhGiaBase):
    id: Optional[str] = Field(None, alias="_id")

class DoiTuongDanhGiaUpdate(BaseModel):
    ten_doi_tuong: Optional[str] = None
    ma_loai_doi_tuong: Optional[str] = None
    ten_loai_doi_tuong: Optional[str] = None
    thuoc_tinh: Optional[Dict[str, Any]] = None
    is_active: Optional[int] = None

class DoiTuongDanhGiaResponse(DoiTuongDanhGiaBase):
    id: str = Field(..., alias="_id")

    class Config:
        populate_by_name = True
