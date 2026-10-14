$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    python -m venv .venv
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$env:PYTHONUTF8 = '1'
& $python -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== Step 1: Port F jaw wiggle over Bluetooth ===" -ForegroundColor Cyan
& $python test_hub_connection.py --transport ble --name Panther
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "=== Step 2: Realtime lip-sync from speaker audio ===" -ForegroundColor Cyan
& $python voice_listener.py -v
