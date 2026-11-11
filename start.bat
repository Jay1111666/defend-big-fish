@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "保卫大肥鱼-十关版.exe" (
    start "" "保卫大肥鱼-十关版.exe"
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    py -3 main.py
)
if errorlevel 1 pause
