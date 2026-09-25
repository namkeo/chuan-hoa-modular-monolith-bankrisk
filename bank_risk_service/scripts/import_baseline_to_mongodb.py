"""Script to import baseline pre-processed JSON payloads from outputs/api/

into MongoDB baseline collections ('rule_findings', 'anomalies', 'clusters', 'ews_indicators', 'stress_test_results').
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from pymongo import MongoClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "outputs" / "api"
MONGO_URI = "mongodb://admin:12345678@localhost:27017/"
DB_NAME = "bank_risk_db"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def import_baseline_payloads():
    print("=======================================================================")
    print(" IMPORTING BASELINE PAYLOADS FROM outputs/api/*.json TO MONGODB")
    print("=======================================================================")
    
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    baseline_files = ["combined.json", "monthly.json", "quarterly.json", "yearly.json", "daily.json"]
    
    rule_findings_all = []
    anomalies_all = []
    clusters_map = {}
    ews_map = {}
    stress_map = {}
    
    for fname in baseline_files:
        fpath = API_DIR / fname
        if not fpath.exists():
            continue
        freq = fname.replace(".json", "")
        print(f"[+] Loading baseline payload: {fname}...")
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            
            # Rule findings
            rules = data.get("rule_findings", [])
            for r in rules:
                r["frequency"] = freq
            rule_findings_all.extend(rules)
            
            # Anomalies
            anoms = data.get("anomalies", [])
            for a in anoms:
                a["frequency"] = freq
            anomalies_all.extend(anoms)
            
            # Clusters
            if "clusters" in data:
                clusters_map[freq] = {"frequency": freq, "data": data["clusters"]}
                
            # EWS
            if "ews" in data:
                ews_map[freq] = {"frequency": freq, "data": data["ews"]}
                
            # Stress
            if "stress" in data:
                stress_map[freq] = {"frequency": freq, "data": data["stress"]}
                
        except Exception as exc:
            print(f"  [-] Failed reading {fname}: {exc}")

    # Import into MongoDB baseline collections
    print("\n--- Saving Baseline Collections in MongoDB ---")
    
    # rule_findings
    coll_rf = db["rule_findings"]
    coll_rf.drop()
    if rule_findings_all:
        coll_rf.insert_many(rule_findings_all)
    print(f"  [+] Imported {len(rule_findings_all)} documents into 'rule_findings'")
    
    # anomalies
    coll_an = db["anomalies"]
    coll_an.drop()
    if anomalies_all:
        coll_an.insert_many(anomalies_all)
    print(f"  [+] Imported {len(anomalies_all)} documents into 'anomalies'")

    # clusters
    coll_cl = db["clusters"]
    coll_cl.drop()
    if clusters_map:
        coll_cl.insert_many(list(clusters_map.values()))
    print(f"  [+] Imported {len(clusters_map)} documents into 'clusters'")

    # ews_indicators
    coll_ews = db["ews_indicators"]
    coll_ews.drop()
    if ews_map:
        coll_ews.insert_many(list(ews_map.values()))
    print(f"  [+] Imported {len(ews_map)} documents into 'ews_indicators'")

    # stress_test_results
    coll_str = db["stress_test_results"]
    coll_str.drop()
    if stress_map:
        coll_str.insert_many(list(stress_map.values()))
    print(f"  [+] Imported {len(stress_map)} documents into 'stress_test_results'")

    print("\n=======================================================================")
    print(" BASELINE PAYLOAD IMPORT COMPLETED SUCCESSFULLY!")
    print("=======================================================================")


if __name__ == "__main__":
    import_baseline_payloads()
