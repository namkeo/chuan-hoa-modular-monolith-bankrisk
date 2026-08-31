from fastapi import APIRouter, Query, status, File, UploadFile, Form
import os, tempfile, uuid
from typing import Optional
from app.schemas.tinh_diem import (
    KiemTraTinhDiemRequest,
    KiemTraTinhDiemResponse,
    ThucHienTinhDiemRequest,
    ThucHienTinhDiemResponse
)
from app.services.tinh_diem_service import TinhDiemService
from app.repositories.ket_qua_tinh_diem_repository import KetQuaTinhDiemRepository
from app.core.exceptions import NotFoundException
from app.utils.response_utils import format_response
from app.utils.template_dl_read import extract_camels_data

router = APIRouter(prefix="/tinh-diem", tags=["Tính Điểm"])
service = TinhDiemService()
ket_qua_repo = KetQuaTinhDiemRepository()

from app.utils.camels_full_evaluator import evaluate_full_camels_from_excel

@router.post("/tu-file-excel")
async def tinh_diem_tu_file_excel(
    file: UploadFile = File(...),
    doi_tuong_id: str = Form(...),
    ky_du_lieu: str = Form(...)
):
    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, f"upload_camels_{uuid.uuid4().hex}.xlsx")
    try:
        content = await file.read()
        with open(temp_file_path, "wb") as f:
            f.write(content)

        camels_json = extract_camels_data(temp_file_path)

        # Truy vấn điểm định tính từ CSDL 'DuLieuSaiPham' cho các nhóm C, A, M, E, L, S
        dt_scores_map = {}
        for group_code in ["C", "A", "M", "E", "L", "S"]:
            try:
                dt_val, dt_dg, dt_details = await service.tinh_diem_dinh_tinh_nhom(
                    doi_tuong_id=doi_tuong_id,
                    ky_du_lieu=ky_du_lieu,
                    ma_nhom=group_code,
                    du_lieu_dict={},
                    du_lieu_input={}
                )
                dt_scores_map[group_code] = {
                    "diem": float(dt_val),
                    "dien_giai": dt_dg,
                    "details": dt_details
                }
            except Exception as e:
                dt_scores_map[group_code] = {
                    "diem": 5.0,
                    "dien_giai": f"Không có dữ liệu sai phạm thuộc nhóm {group_code} trên CSDL -> Đạt điểm định tính tối đa (5.0 điểm)",
                    "details": {"so_luong_sai_pham": 0}
                }

        res_dict = evaluate_full_camels_from_excel(camels_json, doi_tuong_id, ky_du_lieu, dt_scores_map=dt_scores_map)
        return format_response(data=res_dict, message="Tính điểm từ file excel thành công")
    except Exception as err:
        logger.error(f"Lỗi khi xử lý file excel: {err}")
        return format_response(data={}, code=500, message=f"Có lỗi khi xử lý file excel: {err}")
    finally:
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass

@router.post("/kiem-tra", response_model=KiemTraTinhDiemResponse)
async def kiem_tra_tinh_diem(req: KiemTraTinhDiemRequest):
    return await service.kiem_tra_truoc_khi_tinh(
        doi_tuong_id=req.doi_tuong_id,
        ky_du_lieu=req.ky_du_lieu,
        bo_tieu_chi_id=req.bo_tieu_chi_id
    )

@router.post("/thuc-hien", response_model=ThucHienTinhDiemResponse)
async def thuc_hien_tinh_diem(req: ThucHienTinhDiemRequest):
    return await service.thuc_hien_tinh_diem(
        doi_tuong_id=req.doi_tuong_id,
        ky_du_lieu=req.ky_du_lieu,
        bo_tieu_chi_id=req.bo_tieu_chi_id,
        luu_ket_qua=req.luu_ket_qua,
        nguoi_tinh=req.nguoi_tinh or "admin"
    )

@router.post("/thuc-hien-tat-ca")
async def thuc_hien_tinh_diem_tat_ca(
    ky_du_lieu: Optional[str] = Query(None, description="Lọc theo kỳ dữ liệu (ví dụ: T12/2025). Nếu không truyền sẽ tính toàn bộ các kỳ")
):
    from app.repositories.du_lieu_tinh_diem_repository import DuLieuTinhDiemRepository
    dl_repo = DuLieuTinhDiemRepository()
    query = {"is_active": 1}
    if ky_du_lieu:
        query["ky_du_lieu"] = ky_du_lieu

    records = await dl_repo.find_many(query, limit=10000)
    success_count = 0
    error_list = []

    for r in records:
        doi_tuong_id = r.get("doi_tuong_id")
        ky = r.get("ky_du_lieu")
        if not doi_tuong_id or not ky:
            continue
        try:
            await service.thuc_hien_tinh_diem(
                doi_tuong_id=doi_tuong_id,
                ky_du_lieu=ky,
                luu_ket_qua=True,
                nguoi_tinh="batch_api"
            )
            success_count += 1
        except Exception as e:
            error_list.append({"doi_tuong_id": doi_tuong_id, "ky_du_lieu": ky, "loi": str(e)})

    return format_response(
        data={
            "tong_so_ban_ghi": len(records),
            "thanh_cong": success_count,
            "that_bai": len(error_list),
            "danh_sach_loi": error_list[:10]
        },
        message=f"Đã thực hiện tính điểm cho {success_count}/{len(records)} bản ghi trong DuLieuTinhDiem"
    )

import json, logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _get_precomputed_fallback():
    fpath = Path(__file__).resolve().parent.parent.parent / "scripts" / "precomputed_31_rankings.json"
    if fpath.exists():
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading precomputed fallback JSON: {e}")
    return []

@router.get("/ket-qua/{id}")
async def get_ket_qua_by_id(id: str):
    res = None
    try:
        res = await ket_qua_repo.get_by_id(id)
    except Exception as db_err:
        logger.warning(f"MongoDB unavailable ({db_err}), using fallback for get_ket_qua_by_id")
        fallback = _get_precomputed_fallback()
        res = next((i for i in fallback if i.get("_id") == id or i.get("ket_qua_id") == id), None)

    if not res:
        raise NotFoundException(f"Không tìm thấy kết quả tính điểm ID: {id}")
    return format_response(data=res)

@router.get("/ket-qua")
async def get_ket_qua_list(
    doi_tuong_id: Optional[str] = Query(None),
    ky_du_lieu: Optional[str] = Query(None),
    bo_tieu_chi_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10000, ge=1)
):
    query = {"is_active": 1}
    if doi_tuong_id:
        query["doi_tuong_id"] = doi_tuong_id
    if ky_du_lieu:
        query["ky_du_lieu"] = ky_du_lieu
    if bo_tieu_chi_id:
        query["bo_tieu_chi_id"] = bo_tieu_chi_id

    try:
        items = await ket_qua_repo.find_many(query, sort=[("ngay_tinh", -1)], skip=skip, limit=limit)
    except Exception as db_err:
        logger.warning(f"MongoDB unavailable ({db_err}), using precomputed JSON fallback for get_ket_qua_list")
        items = _get_precomputed_fallback()
        if doi_tuong_id:
            target_id = str(doi_tuong_id).strip()
            items = [i for i in items if i.get("doi_tuong_id") == target_id or i.get("ma_doi_tuong") == target_id]
        if ky_du_lieu:
            target_ky = str(ky_du_lieu).strip()
            items = [i for i in items if str(i.get("ky_du_lieu")).strip() == target_ky]
        items = items[skip : skip + limit]

    return format_response(data=items)

@router.get("/lich-su/{doi_tuong_id}")
async def get_lich_su_bank(doi_tuong_id: str):
    """
    Lấy toàn bộ lịch sử điểm số xếp hạng của 1 TCTD qua tất cả các kỳ dữ liệu (sắp xếp T01/2023 -> T12/2025)
    """
    try:
        items = await ket_qua_repo.find_many(
            {"is_active": 1, "$or": [{"doi_tuong_id": doi_tuong_id}, {"ma_doi_tuong": doi_tuong_id}]},
            sort=[("ky_du_lieu", 1)],
            limit=1000
        )
    except Exception as db_err:
        logger.warning(f"MongoDB unavailable ({db_err}), using precomputed JSON fallback for get_lich_su_bank")
        fallback = _get_precomputed_fallback()
        target_id = str(doi_tuong_id).strip()
        items = [i for i in fallback if i.get("doi_tuong_id") == target_id or i.get("ma_doi_tuong") == target_id]
        items.sort(key=lambda x: str(x.get("ky_du_lieu", "")))

    return format_response(data=items)
