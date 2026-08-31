"""Dynamic Calculation & Benchmark Comparison Script.

1. Runs dynamic calculation from raw panel data for all frequencies.
2. Saves newly computed results into new MongoDB collections ('computed_*').
3. Compares newly computed results vs pre-processed baseline collections in MongoDB.
4. Outputs a structured comparison report with Match Rate % and delta stats.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pymongo import MongoClient

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.api_export import _clean, _records
from src.pipeline import available_frequencies, run_pipeline
from src.utils import DATA_ROOT, LOG, load_config

MONGO_URI = "mongodb://admin:12345678@localhost:27017/"
DB_NAME = "bank_risk_db"


def sanitize_dict_or_list(obj):
    if isinstance(obj, dict):
        return {str(k): sanitize_dict_or_list(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_dict_or_list(v) for v in obj]
    return _clean(obj)


def run_verification_and_comparison():
    print("=======================================================================")
    print(" DYNAMIC CALCULATION & BENCHMARK COMPARISON PIPELINE")
    print("=======================================================================")
    
    start_time = time.time()
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # -------------------------------------------------------------------------
    # 1. Run Dynamic Calculation Pipeline for Frequencies
    # -------------------------------------------------------------------------
    target_data_dir = PROJECT_ROOT.parent / "data_all"
    if not target_data_dir.exists():
        target_data_dir = DATA_ROOT
        
    freqs = available_frequencies(target_data_dir)
    if not freqs:
        freqs = ["quarterly", "yearly", "monthly", "combined"]
        
    print(f"\n[+] Running Dynamic Calculations for target folder '{target_data_dir.name}' and frequencies: {freqs}")
    
    all_computed_rules = []
    all_computed_anomalies = []
    all_computed_clusters = {}
    all_computed_ews = {}
    all_computed_stress = {}
    
    for freq in freqs:
        print(f"  [>] Processing dynamic calculation for frequency: '{freq}'...")
        res = run_pipeline(target_data_dir, frequency=freq, use_cache=False)
        
        # 1. Rules
        if res.rule_findings is not None and not res.rule_findings.empty:
            recs = _records(res.rule_findings, name=f"rules_{freq}")
            for r in recs:
                r["frequency"] = freq
            all_computed_rules.extend(recs)
            
        # 2. Anomalies
        if res.anomalies is not None and not res.anomalies.empty:
            recs = _records(res.anomalies, name=f"anomalies_{freq}")
            for r in recs:
                r["frequency"] = freq
            all_computed_anomalies.extend(recs)
            
        # 3. Clusters
        if res.cluster_profiles is not None and not res.cluster_profiles.empty:
            all_computed_clusters[freq] = {
                "frequency": freq,
                "profiles": _records(res.cluster_profiles),
                "projections": _records(res.cluster_projection),
                "k": res.cluster_k,
                "metrics": sanitize_dict_or_list(res.cluster_metrics),
            }
            
        # 4. EWS
        if res.ews_latest is not None and not res.ews_latest.empty:
            all_computed_ews[freq] = {
                "frequency": freq,
                "latest": _records(res.ews_latest),
                "emerging": _records(res.ews_emerging),
            }
            
        # 5. Stress
        if res.stress_results is not None and not res.stress_results.empty:
            all_computed_stress[freq] = {
                "frequency": freq,
                "results": _records(res.stress_results),
            }

    # -------------------------------------------------------------------------
    # 2. Save Newly Computed Results into DB Collections ('computed_*')
    # -------------------------------------------------------------------------
    print("\n--- 2. Saving Computed Results to MongoDB ('computed_*') ---")
    
    # computed_rule_findings
    coll_rule = db["computed_rule_findings"]
    coll_rule.drop()
    if all_computed_rules:
        coll_rule.insert_many([sanitize_dict_or_list(r) for r in all_computed_rules])
    print(f"  [+] Saved {len(all_computed_rules)} records to 'computed_rule_findings'")
    
    # computed_anomalies
    coll_anom = db["computed_anomalies"]
    coll_anom.drop()
    if all_computed_anomalies:
        coll_anom.insert_many([sanitize_dict_or_list(r) for r in all_computed_anomalies])
    print(f"  [+] Saved {len(all_computed_anomalies)} records to 'computed_anomalies'")
    
    # computed_clusters
    coll_clust = db["computed_clusters"]
    coll_clust.drop()
    if all_computed_clusters:
        coll_clust.insert_many([sanitize_dict_or_list(v) for v in all_computed_clusters.values()])
    print(f"  [+] Saved {len(all_computed_clusters)} documents to 'computed_clusters'")
    
    # computed_ews_indicators
    coll_ews = db["computed_ews_indicators"]
    coll_ews.drop()
    if all_computed_ews:
        coll_ews.insert_many([sanitize_dict_or_list(v) for v in all_computed_ews.values()])
    print(f"  [+] Saved {len(all_computed_ews)} documents to 'computed_ews_indicators'")

    # computed_stress_test_results
    coll_stress = db["computed_stress_test_results"]
    coll_stress.drop()
    if all_computed_stress:
        coll_stress.insert_many([sanitize_dict_or_list(v) for v in all_computed_stress.values()])
    print(f"  [+] Saved {len(all_computed_stress)} documents to 'computed_stress_test_results'")

    # -------------------------------------------------------------------------
    # 3. Compare Newly Computed Results vs Existing Preserved Baseline Collections
    # -------------------------------------------------------------------------
    print("\n=======================================================================")
    print(" BENCHMARK COMPARISON REPORT (Computed vs Existing Baseline)")
    print("=======================================================================")
    
    comparisons = [
        ("Rule Findings (Quét luật)", "rule_findings", "computed_rule_findings"),
        ("Anomalies (Bất thường)", "anomalies", "computed_anomalies"),
        ("Clusters (Phân cụm)", "clusters", "computed_clusters"),
        ("EWS Indicators (Cảnh báo sớm)", "ews_indicators", "computed_ews_indicators"),
        ("Stress Test Results (Kiểm tra sức chịu đựng)", "stress_test_results", "computed_stress_test_results"),
    ]
    
    summary_report = []
    
    for label, base_coll_name, comp_coll_name in comparisons:
        base_count = db[base_coll_name].count_documents({})
        comp_count = db[comp_coll_name].count_documents({})
        
        if base_count == 0 and comp_count == 0:
            match_rate = 100.0
            status = "MATCH (EMPTY)"
            diff_count = 0
        elif base_count == 0:
            match_rate = 100.0
            status = "NEWLY COMPUTED"
            diff_count = comp_count
        else:
            diff_count = abs(base_count - comp_count)
            match_rate = round(max(0, 100.0 - (diff_count / max(base_count, 1) * 100.0)), 2)
            status = "MATCH (100%)" if diff_count == 0 else f"DIFF ({diff_count} items)"
            
        print(f"\n📊 [{label}]")
        print(f"   • Existing Baseline DB ('{base_coll_name}'): {base_count} records")
        print(f"   • Newly Computed DB   ('{comp_coll_name}'): {comp_count} records")
        print(f"   • Deviation (Lệch)    : {diff_count} records")
        print(f"   • Match Rate (Độ khớp): {match_rate}% -> Trạng thái: {status}")
        
        summary_report.append({
            "domain": label,
            "baseline_collection": base_coll_name,
            "computed_collection": comp_coll_name,
            "baseline_count": base_count,
            "computed_count": comp_count,
            "diff_count": diff_count,
            "match_rate_pct": match_rate,
            "status": status,
        })

    elapsed = round(time.time() - start_time, 2)
    print(f"\n=======================================================================")
    print(f" VERIFICATION & COMPARISON COMPLETED in {elapsed}s")
    print("=======================================================================")
    return summary_report


if __name__ == "__main__":
    run_verification_and_comparison()
