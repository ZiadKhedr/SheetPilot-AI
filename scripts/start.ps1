param([int]$Port=8000)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath=Join-Path $projectRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) { throw 'Create .venv and install the app dependencies first. See README.md.' }
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'frontend\dist\index.html'))) { throw 'Build the frontend first: pnpm --dir frontend build' }
Write-Host "SheetPilot AI: http://127.0.0.1:$Port"
& $pythonPath -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
