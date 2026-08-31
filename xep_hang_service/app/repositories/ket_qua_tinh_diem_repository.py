from typing import Optional, Dict, Any, List
from app.repositories.base_repository import BaseRepository
from app.utils.mongo_utils import clean_mongo_doc

class KetQuaTinhDiemRepository(BaseRepository):
    collection_name = "KetQuaTinhDiem"

    async def get_by_doi_tuong_and_period(self, doi_tuong_id: str, ky_du_lieu: str, bo_tieu_chi_id: str) -> Optional[Dict[str, Any]]:
        query = {
            "doi_tuong_id": doi_tuong_id,
            "ky_du_lieu": ky_du_lieu,
            "bo_tieu_chi_id": bo_tieu_chi_id,
            "is_active": 1
        }
        return await self.find_one(query)

    async def save_or_update(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        query = {
            "doi_tuong_id": doc["doi_tuong_id"],
            "ky_du_lieu": doc["ky_du_lieu"]
        }
        await self.collection.replace_one(query, doc, upsert=True)
        return clean_mongo_doc(doc)
