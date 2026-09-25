"""Kiểm tra ranh giới sở hữu dữ liệu — bước 1/6 lộ trình Modular Monolith.

Quét toàn bộ mã nguồn tìm mọi điểm truy cập collection MongoDB, rồi đối chiếu với
``docs/architecture/data-ownership.yml``: mỗi collection chỉ được truy cập từ mã
nguồn của module sở hữu nó.

Chạy:
    python scripts/audit/check_data_ownership.py           # báo cáo
    python scripts/audit/check_data_ownership.py --baseline # in lại danh sách nền

Mã thoát 0 khi không có vi phạm MỚI so với ``baseline`` trong tệp yml, 1 khi có.
Chưa gắn vào CI — việc đó thuộc bước 6.

Bắt được 4 dạng truy cập:
    1. trực tiếp    db["coll"].find(...)          db.Coll.insert_one(...)
    2. qua biến     c = db["coll"] ... c.drop()
    3. repository   collection_name = "Coll"      (BaseRepository của module B)
    4. tên động     save_to_mongo("coll", ...)    — khai báo tay ở DYNAMIC_WRITES
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Console Windows mặc định cp1252 không in được tiếng Việt.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MAP_FILE = PROJECT_ROOT / "docs" / "architecture" / "data-ownership.yml"
# scripts/audit bị loại vì chính bộ kiểm tra chứa các chuỗi regex trông như
# tên collection ("Coll", "coll"), sẽ tự báo mình vi phạm.
SKIP_DIRS = ("node_modules", ".git", "__pycache__", ".venv", "dist", "scripts/audit")

# Cả hai lối đặt tên: pymongo/motor dùng snake_case, driver Node dùng camelCase.
WRITE_OPS = (r"insert_one|insertOne|insert_many|insertMany|replace_one|replaceOne"
             r"|update_one|updateOne|update_many|updateMany"
             r"|delete_one|deleteOne|delete_many|deleteMany"
             r"|drop|bulk_write|bulkWrite|create_index|createIndex")
READ_OPS = (r"find_one|findOne|find|count_documents|countDocuments"
            r"|aggregate|distinct")
_WRITE_RE = re.compile(WRITE_OPS)

# Ghi qua hàm bọc nhận tên collection làm tham số — regex không thấy được.
DYNAMIC_WRITES = {
    "bank_risk_service/src/api_export.py": ["api_meta", "api_performance", "api_pdf_status"],
}

_DIRECT = [
    re.compile(r'db\["([a-zA-Z_]+)"\]\s*\.\s*(' + WRITE_OPS + "|" + READ_OPS + r")"),
    re.compile(r"db\.([A-Z][a-zA-Z]+)\s*\.\s*(" + WRITE_OPS + "|" + READ_OPS + r")"),
    re.compile(r'collection\("([a-zA-Z_]+)"\)\s*\.\s*(' + WRITE_OPS + "|" + READ_OPS + r")"),
]
_ASSIGN = [
    re.compile(r'(\w+)\s*=\s*db\["([a-zA-Z_]+)"\]'),
    re.compile(r"(\w+)\s*=\s*db\.([A-Z][a-zA-Z]+)\b"),
    re.compile(r'(\w+)\s*=\s*[\w.]*collection\("([a-zA-Z_]+)"\)'),
]
_REPO = re.compile(r'collection_name\s*[:=]\s*(?:str\s*=\s*)?"([A-Za-z_]+)"')


def load_map() -> dict:
    with MAP_FILE.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def owner_of(cfg: dict) -> dict[str, str]:
    """collection -> tên module sở hữu."""
    out: dict[str, str] = {}
    for mod, spec in cfg["modules"].items():
        for coll in spec.get("owns") or []:
            if coll in out:
                raise SystemExit(f"Lỗi cấu hình: '{coll}' được khai báo ở cả "
                                 f"'{out[coll]}' và '{mod}'")
            out[coll] = mod
    return out


def zone_of(rel: str, cfg: dict) -> str:
    """Vùng mã nguồn -> tên module, hoặc nhãn vùng không sở hữu."""
    best_mod, best_len = None, -1
    for mod, spec in cfg["modules"].items():
        for root in spec.get("code_roots") or []:
            if rel.startswith(root) and len(root) > best_len:
                best_mod, best_len = mod, len(root)
    best_non, best_non_len = None, -1
    for root in cfg.get("non_owners") or {}:
        if rel.startswith(root) and len(root) > best_non_len:
            best_non, best_non_len = root, len(root)
    # tiền tố dài hơn thắng: xep_hang_service/scripts/ đè xep_hang_service/app/
    if best_non_len > best_len:
        return best_non
    return best_mod or best_non or "?"


def scan() -> list[tuple[str, int, str, str]]:
    """-> danh sách (đường dẫn tương đối, số dòng, collection, 'r'|'w')."""
    hits: list[tuple[str, int, str, str]] = []
    files = [p for ext in ("*.py", "*.js")
             for p in PROJECT_ROOT.rglob(ext)
             if not any(d in p.as_posix() for d in SKIP_DIRS)]

    for path in files:
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        text = "\n".join(lines)

        for no, line in enumerate(lines, 1):
            for pat in _DIRECT:
                for m in pat.finditer(line):
                    kind = "w" if _WRITE_RE.fullmatch(m.group(2)) else "r"
                    hits.append((rel, no, m.group(1), kind))
            for m in _REPO.finditer(line):
                hits.append((rel, no, m.group(1), "w"))
                hits.append((rel, no, m.group(1), "r"))

        # gán vào biến rồi dùng biến ở nơi khác trong cùng tệp
        for pat in _ASSIGN:
            for m in pat.finditer(text):
                var, coll = m.group(1), m.group(2)
                no = text[:m.start()].count("\n") + 1
                use = re.compile(re.escape(var) + r"\s*\.\s*(" + WRITE_OPS + "|" + READ_OPS + r")")
                for um in use.finditer(text):
                    kind = "w" if _WRITE_RE.fullmatch(um.group(1)) else "r"
                    hits.append((rel, no, coll, kind))

        for coll in DYNAMIC_WRITES.get(rel, []):
            hits.append((rel, 0, coll, "w"))

    return hits


def violations(cfg: dict) -> dict[tuple[str, str], set[tuple[str, int, str]]]:
    """(vùng, collection) -> các điểm mã vi phạm."""
    owners = owner_of(cfg)
    out: dict[tuple[str, str], set[tuple[str, int, str]]] = defaultdict(set)
    for rel, no, coll, kind in scan():
        owner = owners.get(coll)
        if owner is None:
            out[("<không khai báo>", coll)].add((rel, no, kind))
            continue
        zone = zone_of(rel, cfg)
        if zone != owner:
            out[(zone, coll)].add((rel, no, kind))
    return out


def main(argv: list[str]) -> int:
    cfg = load_map()
    found = violations(cfg)
    keys = sorted(found)

    if "--baseline" in argv:
        print("# dán đoạn này vào data-ownership.yml, khoá 'baseline':")
        print("baseline:")
        for zone, coll in keys:
            print(f'  - "{zone} -> {coll}"')
        return 0

    baseline = set(cfg.get("baseline") or [])
    new = [k for k in keys if f"{k[0]} -> {k[1]}" not in baseline]
    gone = sorted(baseline - {f"{z} -> {c}" for z, c in keys})

    print(f"Quét {MAP_FILE.relative_to(PROJECT_ROOT).as_posix()}: "
          f"{len(owner_of(cfg))} collection, {len(cfg['modules'])} module\n")

    if keys:
        print(f"{len(keys)} cặp (vùng, collection) vượt ranh giới sở hữu:\n")
        for zone, coll in keys:
            tag = "MỚI" if f"{zone} -> {coll}" not in baseline else "nền"
            print(f"  [{tag}] {zone}  ->  {coll}")
            for rel, no, kind in sorted(found[(zone, coll)]):
                where = f"{rel}:{no}" if no else rel
                print(f"          {'ghi' if kind == 'w' else 'đọc'}  {where}")
        print()

    if gone:
        print(f"{len(gone)} vi phạm trong danh sách nền đã được xử lý — "
              f"hãy xoá khỏi 'baseline':")
        for g in gone:
            print(f"  - {g}")
        print()

    if new:
        print(f"THẤT BẠI: {len(new)} vi phạm MỚI ngoài danh sách nền.")
        return 1
    print(f"ĐẠT: không có vi phạm mới ({len(baseline)} vi phạm nền đang chờ xử lý).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
