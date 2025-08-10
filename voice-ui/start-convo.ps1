param()

$ErrorActionPreference = "SilentlyContinue"

# 1) Ensure ODIA TTS is running (port 8002). If you use the Start ODIA button, skip this.
try {
  $h = Invoke-RestMethod "http://localhost:8002/health" -TimeoutSec 3
  if (-not $h) { Write-Host "⚠️  ODIA TTS not responding on 8002. Start it first." -ForegroundColor Yellow }
} catch {
  Write-Host "⚠️  ODIA TTS not responding on 8002. Start it first." -ForegroundColor Yellow
}

# 2) Run Node server
Push-Location $PSScriptRoot
if (Test-Path ".env" -PathType Leaf) { Write-Host "🔐 Loading .env (server will read it)…" }
if (-not (Test-Path "node_modules")) {
  Write-Host "📦 Installing deps…" -ForegroundColor Cyan
  npm install | Out-Null
}

Write-Host "🚀 Starting ODIA Voice UI (http://localhost:3001) …" -ForegroundColor Green
Start-Process powershell -ArgumentList '-NoExit','-Command','cd "$PSScriptRoot"; npm start'
Start-Sleep 2
Start-Process "http://localhost:3001"
Pop-Location
