@echo off
title Bank Risk System Launcher (Docker)
cd /d "%~dp0"

echo =======================================================================
echo     KHOI DONG HE THONG - CHECK DU LIEU MONGO/MINIO AND DOCKER BUILD
echo =======================================================================

echo.
echo [1/3] Khoi chay tat ca dich vu Docker...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [!] Loi khi khoi chay Docker Desktop! Vui long dam bao Docker Desktop da duoc bat.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Kiem tra va tu dong import du lieu neu chua co...
echo   - Module giam sat rui ro (bank_risk_db)...
docker compose exec -T bank_risk_service python /app/scripts/seed_if_empty.py
if %ERRORLEVEL% NEQ 0 (
    python scripts/seed_if_empty.py
)

REM Moi module tu nap du lieu cua minh, trong container cua minh. Truoc day buoc
REM nay chay trong bank_risk_service va import sang xep_hang_service bang sys.path
REM - container do khong co ma cua module nen luon that bai am tham (V6).
echo   - Module xep hang TCTD (credit_scoring_db)...
docker compose exec -T xep_hang_service python scripts/seed_if_empty.py
if %ERRORLEVEL% NEQ 0 (
    echo   [!] Nap du lieu xep hang THAT BAI. Trang Ranking se khong co du lieu.
    echo       Xem lai log ben tren truoc khi tiep tuc.
    pause
)

echo.
echo [3/3] Khoi chay toan bo he thong web va cac dich vu...
docker compose up -d --build
if %ERRORLEVEL% NEQ 0 (
    echo [!] Loi khi thuc hien docker compose up -d --build!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo =======================================================================
echo    HE THONG DA KHOI DONG THANH CONG!
echo    - Web Application:      http://localhost:4000
echo    - FastAPI Risk Service: http://localhost:8080/docs
echo    - Credit Scoring:       http://localhost:8088/docs
echo    - MinIO Console:        http://localhost:9011
echo    - MongoDB Port:         localhost:27018
echo =======================================================================
echo.
docker compose ps
echo.
pause
