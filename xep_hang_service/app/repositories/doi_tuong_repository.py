from typing import Optional, Dict, Any
from app.repositories.base_repository import BaseRepository

class DoiTuongRepository(BaseRepository):
    collection_name = "DoiTuongDanhGia"

    async def get_by_code(self, ma_doi_tuong: str) -> Optional[Dict[str, Any]]:
        return await self.find_one({"ma_doi_tuong": ma_doi_tuong, "is_active": 1})
