from typing import List, Optional, Dict, Any
from app.repositories.chi_tieu_repository import ChiTieuRepository
from app.schemas.chi_tieu import ChiTieuCreate, ChiTieuUpdate
from app.core.exceptions import NotFoundException
from app.services.kiem_tra_cau_hinh_service import KiemTraCauHinhService

class ChiTieuService:
    def __init__(self, repo: Optional[ChiTieuRepository] = None):
        self.repo = repo or ChiTieuRepository()

    async def get_all(
        self,
        bo_tieu_chi_id: Optional[str] = None,
        nhom_tieu_chi_id: Optional[str] = None,
        ma_chi_tieu: Optional[str] = None,
        ma_chi_tieu_goc: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = {}
        if bo_tieu_chi_id:
            query["bo_tieu_chi_id"] = bo_tieu_chi_id
        if nhom_tieu_chi_id:
            query["nhom_tieu_chi_id"] = nhom_tieu_chi_id
        if ma_chi_tieu:
            query["ma_chi_tieu"] = ma_chi_tieu
        if ma_chi_tieu_goc:
            query["ma_chi_tieu_goc"] = ma_chi_tieu_goc
        if is_active is not None:
            query["is_active"] = is_active
        return await self.repo.find_many(query, sort=[("thu_tu_hien_thi", 1)], skip=skip, limit=limit)

    async def get_by_id(self, ct_id: str) -> Dict[str, Any]:
        doc = await self.repo.get_by_id(ct_id)
        if not doc:
            raise NotFoundException(f"Không tìm thấy Chỉ tiêu ID: {ct_id}")
        return doc

    async def create(self, data: ChiTieuCreate) -> Dict[str, Any]:
        doc = data.model_dump(by_alias=True)
        if not doc.get("_id"):
            clean_code = data.ma_chi_tieu.replace(".", "_")
            doc["_id"] = f"CT_{clean_code}"
        return await self.repo.create(doc)

    async def update(self, ct_id: str, data: ChiTieuUpdate) -> Dict[str, Any]:
        await self.get_by_id(ct_id)
        update_dict = data.model_dump(exclude_unset=True)
        return await self.repo.update(ct_id, update_dict)

    async def delete(self, ct_id: str) -> bool:
        await self.get_by_id(ct_id)
        return await self.repo.soft_delete(ct_id)

    async def validate_chi_tieu(self, ct_id: str) -> Dict[str, Any]:
        ct = await self.get_by_id(ct_id)
        errors = []
        errors.extend(KiemTraCauHinhService.kiem_tra_cong_thuc(ct.get("cong_thuc", {}), ct.get("danh_sach_bien", [])))
        for ch in ct.get("cau_hinh_theo_doi_tuong", []):
            errors.extend(KiemTraCauHinhService.kiem_tra_nguong_diem(ch.get("cac_muc_diem", [])))
        return {
            "hop_le": len(errors) == 0,
            "danh_sach_loi": errors
        }
