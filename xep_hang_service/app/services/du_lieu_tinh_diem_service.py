from typing import List, Optional, Dict, Any
from app.repositories.du_lieu_tinh_diem_repository import DuLieuTinhDiemRepository
from app.schemas.du_lieu_tinh_diem import DuLieuTinhDiemCreate, DuLieuTinhDiemUpdate
from app.core.exceptions import NotFoundException
from datetime import datetime

class DuLieuTinhDiemService:
    def __init__(self, repo: Optional[DuLieuTinhDiemRepository] = None):
        self.repo = repo or DuLieuTinhDiemRepository()

    async def get_all(
        self,
        doi_tuong_id: Optional[str] = None,
        ky_du_lieu: Optional[str] = None,
        trang_thai: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = {}
        if doi_tuong_id:
            query["doi_tuong_id"] = doi_tuong_id
        if ky_du_lieu:
            query["ky_du_lieu"] = ky_du_lieu
        if trang_thai:
            query["trang_thai"] = trang_thai
        if is_active is not None:
            query["is_active"] = is_active
        return await self.repo.find_many(query, sort=[("ky_du_lieu", -1), ("phien_ban", -1)], skip=skip, limit=limit)

    async def get_by_id(self, dl_id: str) -> Dict[str, Any]:
        doc = await self.repo.get_by_id(dl_id)
        if not doc:
            raise NotFoundException(f"Không tìm thấy Dữ liệu tính điểm ID: {dl_id}")
        return doc

    async def create(self, data: DuLieuTinhDiemCreate) -> Dict[str, Any]:
        doc = data.model_dump(by_alias=True)
        if not doc.get("_id"):
            clean_dt = data.doi_tuong_id.replace("_", "")
            doc["_id"] = f"DL_{clean_dt}_{data.ky_du_lieu}_V{data.phien_ban}"
        doc["ngay_nhap"] = datetime.now().isoformat()
        return await self.repo.create(doc)

    async def update(self, dl_id: str, data: DuLieuTinhDiemUpdate) -> Dict[str, Any]:
        await self.get_by_id(dl_id)
        update_dict = data.model_dump(exclude_unset=True)
        return await self.repo.update(dl_id, update_dict)

    async def approve(self, dl_id: str, nguoi_phe_duyet: str = "admin") -> Dict[str, Any]:
        await self.get_by_id(dl_id)
        update_dict = {
            "trang_thai": "DA_PHE_DUYET",
            "nguoi_phe_duyet": nguoi_phe_duyet,
            "ngay_phe_duyet": datetime.now().isoformat()
        }
        return await self.repo.update(dl_id, update_dict)

    async def get_car_12_thang(
        self,
        doi_tuong_id: str,
        thoi_gian_t: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lấy chỉ số CAR 12 tháng liên tiếp tính đến mốc thời gian t của 1 Ngân hàng
        """
        dt_t = self._parse_thoi_gian_t(thoi_gian_t)

        # If default time is now (e.g. 2026) but DB has data for 2025, fallback to latest dataset period if no query time passed
        if not thoi_gian_t:
            latest_docs = await self.repo.find_many({"doi_tuong_id": doi_tuong_id}, sort=[("ky_du_lieu", -1)], limit=1)
            if latest_docs and latest_docs[0].get("ky_du_lieu"):
                ky = latest_docs[0]["ky_du_lieu"]
                if "/" in ky:
                    parts = ky.replace("T", "").split("/")
                    if len(parts) == 2:
                        try:
                            m, y = int(parts[0]), int(parts[1])
                            dt_t = datetime(y, m, 28)
                        except Exception:
                            pass

        year = dt_t.year
        month = dt_t.month

        month_tuples = []
        for i in range(11, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            month_tuples.append((y, m))

        target_kys = []
        month_info = []
        for y, m in month_tuples:
            ky_str1 = f"T{m:02d}/{y}"
            ky_str2 = f"T{m}/{y}"
            ky_str3 = f"{y}-{m:02d}"
            ky_str4 = f"{m:02d}/{y}"
            target_kys.extend([ky_str1, ky_str2, ky_str3, ky_str4])
            month_info.append({
                "nam": y,
                "thang": m,
                "ky_primary": ky_str1,
                "possible_kys": [ky_str1, ky_str2, ky_str3, ky_str4]
            })

        docs = await self.repo.find_many({"doi_tuong_id": doi_tuong_id, "ky_du_lieu": {"$in": target_kys}}, limit=200)
        doc_map = {d.get("ky_du_lieu"): d for d in docs}

        CAR_KEYS = [
            "Tỷ lệ an toàn vốn tối thiểu (CAR) (riêng lẻ)",
            "Tỷ lệ an toàn vốn tối thiểu (CAR)",
            "Tỷ lệ an toàn vốn",
            "R-101",
            "R-105",
            "R-102",
            "1.1",
            "1.1.a",
            "CAR"
        ]

        results = []
        car_values = []

        for item in month_info:
            matched_doc = None
            for k in item["possible_kys"]:
                if k in doc_map:
                    matched_doc = doc_map[k]
                    break

            car_val = None
            if matched_doc:
                du_lieu = matched_doc.get("du_lieu", {})
                if isinstance(du_lieu, dict):
                    for ck in CAR_KEYS:
                        if ck in du_lieu and du_lieu[ck] is not None:
                            try:
                                car_val = round(float(du_lieu[ck]), 3)
                                break
                            except Exception:
                                pass

            if car_val is not None:
                car_values.append(car_val)

            results.append({
                "ky_du_lieu": item["ky_primary"],
                "nam": item["nam"],
                "thang": item["thang"],
                "car": car_val
            })

        car_trung_binh = round(sum(car_values) / len(car_values), 3) if car_values else None
        car_cao_nhat = max(car_values) if car_values else None
        car_thap_nhat = min(car_values) if car_values else None

        return {
            "doi_tuong_id": doi_tuong_id,
            "thoi_gian_t": dt_t.isoformat(),
            "so_luong_thang": len(results),
            "du_lieu_car": results,
            "car_trung_binh": car_trung_binh,
            "car_cao_nhat": car_cao_nhat,
            "car_thap_nhat": car_thap_nhat
        }

    @staticmethod
    def _parse_thoi_gian_t(t_str: Optional[str]) -> datetime:
        if not t_str or str(t_str).strip() == "":
            return datetime.now()

        clean_t = str(t_str).strip()
        if "/" in clean_t:
            parts = clean_t.replace("T", "").split("/")
            if len(parts) == 2:
                try:
                    m, y = int(parts[0]), int(parts[1])
                    return datetime(y, m, 28)
                except Exception:
                    pass

        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m", "%Y/%m/%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(clean_t[:10], fmt[:10])
            except Exception:
                pass

        return datetime.now()
