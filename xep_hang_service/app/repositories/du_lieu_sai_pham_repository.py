from typing import List, Dict, Any
from app.repositories.base_repository import BaseRepository

class DuLieuSaiPhamRepository(BaseRepository):
    collection_name = "DuLieuSaiPham"

    async def get_by_doi_tuong_and_ky(self, doi_tuong_id: str, ky_du_lieu: str) -> List[Dict[str, Any]]:
        import asyncio
        query = {
            "doi_tuong_id": doi_tuong_id,
            "ky_du_lieu": ky_du_lieu,
            "is_active": 1
        }
        try:
            cursor = self.collection.find(query)
            return await asyncio.wait_for(cursor.to_list(length=1000), timeout=0.1)
        except Exception:
            return []

    async def get_by_doi_tuong_ky_and_nhom(self, doi_tuong_id: str, ky_du_lieu: str, ma_nhom_chi_tieu: str) -> List[Dict[str, Any]]:
        import asyncio
        ma_nhom_clean = ma_nhom_chi_tieu.replace("NTC_", "").upper()
        query = {
            "doi_tuong_id": doi_tuong_id,
            "ky_du_lieu": ky_du_lieu,
            "$or": [
                {"ma_nhom_chi_tieu": ma_nhom_clean},
                {"ma_nhom_chi_tieu": f"NTC_{ma_nhom_clean}"}
            ],
            "is_active": 1
        }
        try:
            cursor = self.collection.find(query)
            return await asyncio.wait_for(cursor.to_list(length=1000), timeout=0.1)
        except Exception:
            return []
