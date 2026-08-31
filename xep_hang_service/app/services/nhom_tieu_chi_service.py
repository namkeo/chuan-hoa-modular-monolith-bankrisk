from typing import List, Optional, Dict, Any
from app.repositories.nhom_tieu_chi_repository import NhomTieuChiRepository
from app.schemas.nhom_tieu_chi import NhomTieuChiCreate, NhomTieuChiUpdate
from app.core.exceptions import NotFoundException

class NhomTieuChiService:
    def __init__(self, repo: Optional[NhomTieuChiRepository] = None):
        self.repo = repo or NhomTieuChiRepository()

    async def get_all(
        self,
        bo_tieu_chi_id: Optional[str] = None,
        ma_nhom: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = {}
        if bo_tieu_chi_id:
            query["bo_tieu_chi_id"] = bo_tieu_chi_id
        if ma_nhom:
            query["ma_nhom"] = ma_nhom
        if is_active is not None:
            query["is_active"] = is_active
        return await self.repo.find_many(query, sort=[("thu_tu_hien_thi", 1)], skip=skip, limit=limit)

    async def get_by_id(self, ntc_id: str) -> Dict[str, Any]:
        doc = await self.repo.get_by_id(ntc_id)
        if not doc:
            raise NotFoundException(f"Không tìm thấy Nhóm tiêu chí ID: {ntc_id}")
        return doc

    async def create(self, data: NhomTieuChiCreate) -> Dict[str, Any]:
        doc = data.model_dump(by_alias=True)
        if not doc.get("_id"):
            doc["_id"] = f"NTC_{data.ma_nhom}"
        return await self.repo.create(doc)

    async def update(self, ntc_id: str, data: NhomTieuChiUpdate) -> Dict[str, Any]:
        await self.get_by_id(ntc_id)
        update_dict = data.model_dump(exclude_unset=True)
        return await self.repo.update(ntc_id, update_dict)

    async def delete(self, ntc_id: str) -> bool:
        await self.get_by_id(ntc_id)
        return await self.repo.soft_delete(ntc_id)
