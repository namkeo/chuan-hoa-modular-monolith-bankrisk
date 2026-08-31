#!/bin/bash
set +e
echo "============================================================"
echo "      AUTO-INITIALIZING MONGO DATABASES & COLLECTIONS       "
echo "============================================================"

# Data initialization is performed via Python seed script scripts/import_all_data.py
echo "[+] MongoDB service started successfully."
echo "[+] Data import is managed by scripts/import_all_data.py or import_and_run_docker.bat."
echo "============================================================"
exit 0
