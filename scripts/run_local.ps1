# Run NEXUS Ops Locally in Windows PowerShell
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  NEXUS Ops — Payment Reliability & Incident Intelligence " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Start Backend in Background
Write-Host "[1/2] Starting Backend API on http://localhost:8000..." -ForegroundColor Yellow
Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "backend"

# 2. Start Frontend
Write-Host "[2/2] Starting Frontend Vite Dev Server on http://localhost:5173..." -ForegroundColor Yellow
Set-Location "frontend"
npm run dev
