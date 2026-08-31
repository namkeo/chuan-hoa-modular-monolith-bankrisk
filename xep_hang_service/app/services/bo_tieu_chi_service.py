from typing import List, Optional, Dict, Any
from app.repositories.bo_tieu_chi_repository import BoTieuChiRepository
from app.schemas.bo_tieu_chi import BoTieuChiCreate, BoTieuChiUpdate
from app.core.exceptions import NotFoundException, ConfigurationException
from datetime import datetime

class BoTieuChiService:
    def __init__(self, repo: Optional[BoTieuChiRepository] = None):
        self.repo = repo or BoTieuChiRepository()

    async def get_all(self, skip: int = 0, limit: int = 100, is_active: Optional[int] = 1) -> List[Dict[str, Any]]:
        query = {}
        if is_active is not None:
            query["is_active"] = is_active
        return await self.repo.find_many(query, sort=[("phien_ban", -1)], skip=skip, limit=limit)

    async def get_by_id(self, btc_id: str) -> Dict[str, Any]:
        doc = await self.repo.get_by_id(btc_id)
        if not doc:
            raise NotFoundException(f"Không tìm thấy Bộ tiêu chí ID: {btc_id}")
        return doc

    async def create(self, data: BoTieuChiCreate) -> Dict[str, Any]:
        doc = data.model_dump(by_alias=True)
        if not doc.get("_id"):
            doc["_id"] = f"{data.ma_bo_tieu_chi}_V{data.phien_ban}"
        doc["ngay_tao"] = datetime.now().isoformat()
        return await self.repo.create(doc)

    async def update(self, btc_id: str, data: BoTieuChiUpdate) -> Dict[str, Any]:
        existing = await self.get_by_id(btc_id)
        # Check if already used in results before updating directly
        update_dict = data.model_dump(exclude_unset=True)
        update_dict["ngay_cap_nhat"] = datetime.now().isoformat()
        res = await self.repo.update(btc_id, update_dict)
        return res

    async def delete(self, btc_id: str) -> bool:
        await self.get_by_id(btc_id)
        return await self.repo.soft_delete(btc_id)

    async def publish(self, btc_id: str) -> Dict[str, Any]:
        doc = await self.get_by_id(btc_id)
        # Deactivate any existing active version
        active = await self.repo.get_active_bo_tieu_chi()
        if active and active["_id"] != btc_id:
            await self.repo.update(active["_id"], {"trang_thai": "NGUNG_AP_DUNG"})

        return await self.repo.update(btc_id, {"trang_thai": "DANG_AP_DUNG"})
