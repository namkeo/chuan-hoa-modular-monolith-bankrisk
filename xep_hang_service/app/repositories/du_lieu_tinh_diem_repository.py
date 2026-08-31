from typing import Optional, Dict, Any
from app.repositories.base_repository import BaseRepository

class DuLieuTinhDiemRepository(BaseRepository):
    collection_name = "DuLieuTinhDiem"

    async def get_input_data(self, doi_tuong_id: str, ky_du_lieu: str) -> Optional[Dict[str, Any]]:
        query = {
            "doi_tuong_id": doi_tuong_id,
            "ky_du_lieu": ky_du_lieu,
            "trang_thai": "DA_PHE_DUYET",
            "is_active": 1
        }
        # Sort by version descending to pick latest version if multiple
        return await self.find_one(query)
