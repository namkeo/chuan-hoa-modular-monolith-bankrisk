"""Script to import all JSON seed files into MongoDB (bank_risk_db & credit_scoring_db)
and verify MinIO host file mounting.
"""
from __future__ import annotations

import os
import sys
import time
import pathlib
import bson.json_util as json_util
from pymongo import MongoClient

# Ensure stdout uses UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27018/")

BATCH_SIZE = 2000


def seed_database(client: MongoClient, db_name: str, json_dir: pathlib.Path):
    if not json_dir.exists():
        print(f"  [!] Directory not found: {json_dir}")
        return

    db = client[db_name]
    print(f"\n--- Importing into Database: '{db_name}' ---")
    json_files = sorted(json_dir.glob("*.json"))

    for fpath in json_files:
        cname = fpath.stem
        file_size_mb = fpath.stat().st_size / (1024 * 1024)
        print(f"  [+] Processing '{cname}' ({file_size_mb:.2f} MB)...")

        try:
            content = fpath.read_text(encoding="utf-8")
            docs = json_util.loads(content)
        except Exception as err:
            print(f"      [!] Error loading {fpath.name}: {err}")
            continue

        if not docs:
            print(f"      [-] File '{fpath.name}' is empty. Skipping.")
            continue

        if isinstance(docs, dict):
            docs = [docs]

        coll = db[cname]
        coll.drop()

        total = len(docs)
        inserted = 0

        for i in range(0, total, BATCH_SIZE):
            chunk = docs[i: i + BATCH_SIZE]
            coll.insert_many(chunk)
            inserted += len(chunk)

        print(f"      [✓] Successfully imported {inserted}/{total} documents into '{cname}'")


def verify_minio():
    print("\n--- Verifying MinIO Storage Directory ---")
    minio_dir = PROJECT_ROOT / "minio_data" / "bankrisk-files"
    if minio_dir.exists():
        files = list(minio_dir.glob("*"))
        print(f"  [✓] MinIO host directory contains {len(files)} files/folders ready to serve.")
    else:
        print(f"  [!] MinIO directory not found at {minio_dir}")


def main():
    print("=======================================================================")
    print("          IMPORTING ALL JSON SEED PAYLOADS INTO MONGODB               ")
    print("=======================================================================")
    print(f"Connecting to MongoDB at: {MONGO_URI}")

    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("  [✓] MongoDB Connection Established Successfully on port 27018!")
    except Exception:
        alt_uri = "mongodb://admin:12345678@localhost:27017/"
        try:
            print(f"  [!] Port 27018 unavailable, trying alternative URI: {alt_uri}")
            client = MongoClient(alt_uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            print("  [✓] MongoDB Connection Established Successfully on port 27017!")
        except Exception as exc2:
            print(f"  [X] Failed to connect to MongoDB: {exc2}")
            print("      Please ensure MongoDB container is running ('docker compose up -d mongodb').")
            sys.exit(1)

    start_t = time.time()

    # 1. Seed bank_risk_db
    bank_risk_dir = PROJECT_ROOT / "mongo_data" / "init_json" / "bank_risk_db"
    seed_database(client, "bank_risk_db", bank_risk_dir)

    # 2. Seed credit_scoring_db
    scoring_dir = PROJECT_ROOT / "mongo_data" / "init_json" / "credit_scoring_db"
    seed_database(client, "credit_scoring_db", scoring_dir)

    # 3. Verify MinIO
    verify_minio()

    elapsed = time.time() - start_t
    print("\n=======================================================================")
    print(f" [✓] ALL DATA IMPORTED SUCCESSFULLY IN {elapsed:.2f} SECONDS!")
    print("=======================================================================")


if __name__ == "__main__":
    main()
