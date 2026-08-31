@echo off
title Bank Risk System Launcher (Docker)
cd /d "%~dp0"

echo =======================================================================
echo     KHOI DONG HE THONG - CHECK DU LIEU MONGO/MINIO AND DOCKER BUILD
echo =======================================================================

echo.
echo [1/3] Khoi chay MongoDB va MinIO...
docker compose up -d mongodb minio
if %ERRORLEVEL% NEQ 0 (
    echo [!] Loi khi khoi chay mongodb va minio! Vui long dam bao Docker Desktop da bat va WSL2 khong bi loi.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Kiem tra va tu dong import du lieu neu chua co...
python scripts/seed_if_empty.py

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
