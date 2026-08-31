@echo off
chcp 65001 > nul
set PYTHONPATH=%~dp0..
"C:\Users\thuynx1\AppData\Local\miniconda3\envs\source_code\python.exe" -u "%~dp0load_all_31_excel_rankings.py"
