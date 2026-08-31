from typing import Any, Dict, Optional, List

def format_response(
    data: Any = None,
    message: str = "Thành công",
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format response JSON chuẩn cho API.
    """
    res = {
        "success": True,
        "message": message,
        "data": data
    }
    if meta is not None:
        res["meta"] = meta
    return res

def format_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int,
    message: str = "Thành công"
) -> Dict[str, Any]:
    """
    Format response phân trang cho danh sách API.
    """
    return {
        "success": True,
        "message": message,
        "data": items,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit if limit > 0 else 1
        }
    }
