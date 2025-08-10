# Kills Node that runs the Voice UI
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "🛑 Stopped ODIA Voice UI (node)" -ForegroundColor Green
