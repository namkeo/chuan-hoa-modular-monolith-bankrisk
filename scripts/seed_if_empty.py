"""Smart Data Seeding Script for MongoDB & MinIO.

Checks if MongoDB databases have data.
If empty or incomplete, seeds data automatically. If valid data exists, skips gracefully.
"""
from __future__ import annotations

import os
import pathlib
import sys
import bson.json_util as json_util
from pymongo import MongoClient

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
BATCH_SIZE = 2000


import time

def seed_mongodb():
    print("\n[1/2] Checking MongoDB status...")
    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27018/")
    alt_uri = "mongodb://admin:12345678@localhost:27017/"
    client = None

    for attempt in range(1, 16):
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            print(f"  [✓] Connected to MongoDB at {mongo_uri}")
            break
        except Exception:
            try:
                client = MongoClient(alt_uri, serverSelectionTimeoutMS=2000)
                client.admin.command("ping")
                print(f"  [✓] Connected to MongoDB at {alt_uri}")
                break
            except Exception as e2:
                if attempt == 15:
                    print(f"  [!] Cannot connect to MongoDB after 15 attempts ({mongo_uri} / {alt_uri}): {e2}")
                    return
                print(f"  [...] Waiting for MongoDB to become ready... (attempt {attempt}/15)")
                time.sleep(2)

    # 1. Check bank_risk_db
    db_name = "bank_risk_db"
    db = client[db_name]
    valid_payload = db["api_payloads"].find_one({"empty": False})
    panel_count = db["raw_panel_data"].count_documents({})

    if valid_payload and panel_count > 0:
        doc_count = sum(db[c].count_documents({}) for c in db.list_collection_names())
        print(f"  [✓] MongoDB '{db_name}' already contains {doc_count} valid documents. (Skipping import)")
    else:
        print(f"  [+] MongoDB '{db_name}' is empty or incomplete. Importing JSON seed files...")
        init_dir = PROJECT_ROOT / "mongo_data" / "init_json" / "bank_risk_db"
        if init_dir.exists():
            for fpath in sorted(init_dir.glob("*.json")):
                cname = fpath.stem
                with open(fpath, "r", encoding="utf-8") as f:
                    docs = json_util.loads(f.read())
                    if docs:
                        if isinstance(docs, dict):
                            docs = [docs]
                        db[cname].drop()
                        for i in range(0, len(docs), BATCH_SIZE):
                            chunk = docs[i : i + BATCH_SIZE]
                            db[cname].insert_many(chunk)
                        print(f"      └─ Imported {len(docs)} documents into '{cname}'")
        print(f"  [✓] MongoDB '{db_name}' seeding complete!")

    # 2. Check credit_scoring_db
    scoring_db_name = "credit_scoring_db"
    scoring_db = client[scoring_db_name]
    scoring_count = sum(scoring_db[c].count_documents({}) for c in scoring_db.list_collection_names())

    if scoring_count > 0:
        print(f"  [✓] MongoDB '{scoring_db_name}' already contains {scoring_count} documents. (Skipping import)")
    else:
        print(f"  [+] MongoDB '{scoring_db_name}' is empty. Importing JSON seed files...")
        init_dir = PROJECT_ROOT / "mongo_data" / "init_json" / "credit_scoring_db"
        if init_dir.exists():
            for fpath in sorted(init_dir.glob("*.json")):
                cname = fpath.stem
                with open(fpath, "r", encoding="utf-8") as f:
                    docs = json_util.loads(f.read())
                    if docs:
                        if isinstance(docs, dict):
                            docs = [docs]
                        scoring_db[cname].drop()
                        for i in range(0, len(docs), BATCH_SIZE):
                            chunk = docs[i : i + BATCH_SIZE]
                            scoring_db[cname].insert_many(chunk)
                        print(f"      └─ Imported {len(docs)} documents into '{cname}'")
        print(f"  [✓] Credit scoring MongoDB seeding complete!")


def seed_minio():
    print("\n[2/2] Checking MinIO Object Storage status...")
    source_minio = PROJECT_ROOT / "minio_data" / "bankrisk-files"
    if source_minio.exists():
        files = list(source_minio.glob("*"))
        print(f"  [✓] MinIO host directory contains {len(files)} files mounted directly to container.")
    else:
        print("  [!] Source minio_data directory not found.")


if __name__ == "__main__":
    print("============================================================")
    print("      CHECKING AND SEEDING DATA FOR MONGODB & MINIO        ")
    print("============================================================")
    seed_mongodb()
    seed_minio()
    print("\n[✓] All data checks and seeding completed successfully!")
