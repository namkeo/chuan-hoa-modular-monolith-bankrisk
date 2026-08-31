from typing import List, Dict, Any, Optional
from app.repositories.base_repository import BaseRepository

class ChiTieuRepository(BaseRepository):
    collection_name = "ChiTieu"

    async def get_by_bo_tieu_chi(self, bo_tieu_chi_id: str, only_active: bool = True) -> List[Dict[str, Any]]:
        query = {"bo_tieu_chi_id": bo_tieu_chi_id}
        if only_active:
            query["is_active"] = 1
        return await self.find_many(query, sort=[("thu_tu_hien_thi", 1)])

    async def get_by_nhom_tieu_chi(self, bo_tieu_chi_id: str, nhom_tieu_chi_id: str, only_active: bool = True) -> List[Dict[str, Any]]:
        query = {"bo_tieu_chi_id": bo_tieu_chi_id, "nhom_tieu_chi_id": nhom_tieu_chi_id}
        if only_active:
            query["is_active"] = 1
        return await self.find_many(query, sort=[("thu_tu_hien_thi", 1)])

    async def get_by_ma_chi_tieu_goc(self, bo_tieu_chi_id: str, ma_chi_tieu_goc: str, only_active: bool = True) -> List[Dict[str, Any]]:
        query = {"bo_tieu_chi_id": bo_tieu_chi_id, "ma_chi_tieu_goc": ma_chi_tieu_goc}
        if only_active:
            query["is_active"] = 1
        return await self.find_many(query)
