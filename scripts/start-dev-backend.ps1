# Backend con recarga automática (uvicorn --reload).
# Uso: .\scripts\start-dev-backend.ps1  (desde la raíz del monorepo)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\backend

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Crea el venv primero: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
