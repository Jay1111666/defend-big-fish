@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv-web\Scripts\python.exe" (
    echo 尚未安装网页版环境，请参阅 web\README.md。
    pause
    exit /b 1
)
".venv-web\Scripts\python.exe" -u tools\serve_web.py
if errorlevel 1 pause
