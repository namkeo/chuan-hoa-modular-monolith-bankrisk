from typing import Any

def clean_mongo_doc(doc: Any) -> Any:
    """
    Chuẩn hóa document từ MongoDB để trả về JSON API (chuyển ObjectId thành str).
    """
    if doc is None:
        return None
    if isinstance(doc, list):
        return [clean_mongo_doc(item) for item in doc]
    if isinstance(doc, dict):
        cleaned = {}
        for k, v in doc.items():
            if k == "_id":
                cleaned["_id"] = str(v)
            elif isinstance(v, (dict, list)):
                cleaned[k] = clean_mongo_doc(v)
            else:
                cleaned[k] = v
        return cleaned
    return doc
