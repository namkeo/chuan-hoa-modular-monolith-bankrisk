from typing import Optional, Dict, Any
from app.repositories.base_repository import BaseRepository

class BoTieuChiRepository(BaseRepository):
    collection_name = "BoTieuChi"

    async def get_active_bo_tieu_chi(self) -> Optional[Dict[str, Any]]:
        return await self.find_one({"trang_thai": "DANG_AP_DUNG", "is_active": 1})

    async def get_by_code_and_version(self, ma_bo_tieu_chi: str, phien_ban: int) -> Optional[Dict[str, Any]]:
        return await self.find_one({"ma_bo_tieu_chi": ma_bo_tieu_chi, "phien_ban": phien_ban})
