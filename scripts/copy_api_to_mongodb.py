"""Copy all JSON data from outputs/api directly into MongoDB collections.

Handles MongoDB's 16MB single-document limit by splitting large nested arrays
(rule_findings, scores, anomalies, series, ews, stress, validation) into dedicated
collections, while storing frequency summaries in api_payloads.

MongoDB URI: mongodb://admin:12345678@localhost:27017/
Database: bank_risk_db
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from pymongo import MongoClient

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import OUTPUTS_DIR

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:12345678@localhost:27017/")
DB_NAME = "bank_risk_db"
API_DIR = OUTPUTS_DIR / "api"


def clean_bson(obj):
    """Ensure dictionary keys and values are BSON compatible."""
    if isinstance(obj, dict):
        return {str(k): clean_bson(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_bson(v) for v in obj]
    else:
        return obj


def copy_api_files_to_mongodb():
    start_time = time.time()
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    print(f"Target Database: '{DB_NAME}'")

    if not API_DIR.exists():
        print(f"Error: API directory '{API_DIR}' does not exist.")
        return

    json_files = sorted(API_DIR.glob("*.json"))
    print(f"Found {len(json_files)} JSON file(s) in '{API_DIR}':")
    for f in json_files:
        print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")

    print("\n--- Importing JSON files into MongoDB ---")

    # Define collections
    coll_payloads = db["api_payloads"]
    coll_meta = db["api_meta"]
    coll_perf = db["api_performance"]
    coll_pdf = db["api_pdf_status"]
    
    coll_rankings = db["bank_rankings"]
    coll_scores = db["risk_scores"]
    coll_findings = db["rule_findings"]
    coll_anomalies = db["anomalies"]
    coll_files = db["raw_files"]
    coll_validation = db["validation_findings"]
    coll_high_risk = db["high_risk_periods"]
    coll_stress_sys = db["systemic_stress"]
    coll_clusters = db["clusters"]
    coll_ews = db["ews_indicators"]
    coll_stress = db["stress_test_results"]
    coll_series = db["time_series_data"]

    # Drop existing collections for clean sync
    all_colls = [coll_payloads, coll_meta, coll_perf, coll_pdf, coll_rankings, 
                 coll_scores, coll_findings, coll_anomalies, coll_files, 
                 coll_validation, coll_high_risk, coll_stress_sys,
                 coll_clusters, coll_ews, coll_stress, coll_series]
    for coll in all_colls:
        coll.drop()

    for fpath in json_files:
        print(f"\nProcessing '{fpath.name}'...")
        with open(fpath, "r", encoding="utf-8") as f:
            content = json.load(f)

        content = clean_bson(content)

        if fpath.name == "meta.json":
            coll_meta.insert_one(content)
            print("  [+] Inserted document into 'api_meta'")
        elif fpath.name == "performance.json":
            coll_perf.insert_one(content)
            print("  [+] Inserted document into 'api_performance'")
        elif fpath.name == "pdf_status.json":
            coll_pdf.insert_one(content)
            print("  [+] Inserted document into 'api_pdf_status'")
        else:  # Frequency payloads (<freq>.json)
            freq = content.get("frequency", fpath.stem)

            # Extract large arrays to dedicated collections to avoid 16MB BSON limit
            rf = content.pop("rule_findings", [])
            sc = content.pop("scores", [])
            an = content.pop("anomalies", [])
            rk = content.pop("ranking", [])
            vl = content.pop("validation", [])
            fl = content.pop("files", [])
            hr = content.pop("high_risk_periods", [])
            ss = content.pop("systemic_stress", [])
            cl = content.pop("clusters", {})
            ews = content.pop("ews", {})
            str_data = content.pop("stress", {})
            series = content.pop("series", {})

            # 1. Save frequency payload summary & metadata document in api_payloads
            coll_payloads.replace_one({"frequency": freq}, content, upsert=True)
            print(f"  [+] Saved frequency metadata document for '{freq}' in 'api_payloads'")

            # 2. Insert extracted collections with frequency tag
            if rf:
                for r in rf: r["frequency"] = freq
                coll_findings.insert_many(rf)
                print(f"      -> Inserted {len(rf)} rule findings into 'rule_findings'")

            if sc:
                for r in sc: r["frequency"] = freq
                coll_scores.insert_many(sc)
                print(f"      -> Inserted {len(sc)} risk scores into 'risk_scores'")

            if an:
                for r in an: r["frequency"] = freq
                coll_anomalies.insert_many(an)
                print(f"      -> Inserted {len(an)} anomalies into 'anomalies'")

            if rk:
                for r in rk: r["frequency"] = freq
                coll_rankings.insert_many(rk)
                print(f"      -> Inserted {len(rk)} rankings into 'bank_rankings'")

            if fl and freq == "combined":
                coll_files.insert_many(fl)
                print(f"      -> Inserted {len(fl)} file records into 'raw_files'")

            if vl:
                for r in vl: r["frequency"] = freq
                coll_validation.insert_many(vl)
                print(f"      -> Inserted {len(vl)} validation entries into 'validation_findings'")

            if hr:
                for r in hr: r["frequency"] = freq
                coll_high_risk.insert_many(hr)
                print(f"      -> Inserted {len(hr)} high risk periods into 'high_risk_periods'")

            if ss:
                for r in ss: r["frequency"] = freq
                coll_stress_sys.insert_many(ss)
                print(f"      -> Inserted {len(ss)} systemic stress records into 'systemic_stress'")

            if cl:
                cl["frequency"] = freq
                coll_clusters.insert_one(cl)
                print(f"      -> Inserted cluster models for '{freq}' into 'clusters'")

            if ews:
                ews["frequency"] = freq
                coll_ews.insert_one(ews)
                print(f"      -> Inserted EWS payload for '{freq}' into 'ews_indicators'")

            if str_data:
                str_data["frequency"] = freq
                coll_stress.insert_one(str_data)
                print(f"      -> Inserted Stress Test payload for '{freq}' into 'stress_test_results'")

            if series:
                series["frequency"] = freq
                coll_series.insert_one(series)
                print(f"      -> Inserted Time Series payload for '{freq}' into 'time_series_data'")

    # Create Indexes for high performance querying
    print("\n--- Creating Database Indexes ---")
    coll_payloads.create_index([("frequency", 1)], unique=True)
    coll_findings.create_index([("bank_id", 1), ("period", 1), ("frequency", 1)])
    coll_findings.create_index([("severity", 1)])
    coll_scores.create_index([("bank_id", 1), ("period", 1), ("frequency", 1)])
    coll_anomalies.create_index([("bank_id", 1), ("period", 1), ("frequency", 1)])
    coll_rankings.create_index([("bank_id", 1), ("period", 1), ("frequency", 1)])
    coll_validation.create_index([("category", 1), ("bank_id", 1)])
    print("  [+] Indexes created successfully.")

    elapsed = time.time() - start_time
    print(f"\n=======================================================")
    print(f" SUCCESS: COPIED ALL outputs/api DATA TO MONGODB")
    print(f" Execution Time: {elapsed:.2f} seconds")
    print(f" Database: {DB_NAME}")
    print(f" Collections in '{DB_NAME}':")
    for name in sorted(db.list_collection_names()):
        count = db[name].count_documents({})
        print(f"   - {name:<28}: {count:>8} docs")
    print(f"=======================================================")


if __name__ == "__main__":
    copy_api_files_to_mongodb()
