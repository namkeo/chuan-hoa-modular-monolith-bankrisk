from typing import List, Dict, Any
from app.repositories.base_repository import BaseRepository

class NhomTieuChiRepository(BaseRepository):
    collection_name = "NhomTieuChi"

    async def get_by_bo_tieu_chi(self, bo_tieu_chi_id: str, only_active: bool = True) -> List[Dict[str, Any]]:
        query = {"bo_tieu_chi_id": bo_tieu_chi_id}
        if only_active:
            query["is_active"] = 1
        return await self.find_many(query, sort=[("thu_tu_hien_thi", 1), ("so_thu_tu", 1)])
