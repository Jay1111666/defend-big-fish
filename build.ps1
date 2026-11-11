$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$assetPath = Join-Path $PSScriptRoot 'assets'
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name '保卫大肥鱼-十关版' --distpath . --workpath build --specpath build --add-data "$assetPath;assets" main.py
if ($LASTEXITCODE -ne 0) { throw '打包失败' }
