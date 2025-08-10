param([int]$UiPort = 5173)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_PY = "C:\Users\OD~IA\odia-tts\Scripts\python.exe"  # your working venv python
if (-not (Test-Path $VENV_PY)) { $VENV_PY = "python" }

function Load-EnvFile([string]$path) {
  if (-not (Test-Path $path)) { return }
  Get-Content $path | ForEach-Object {
    if ($_ -match '^\s*(#|$)') { return }
    $name,$value = $_ -split '=',2
    if (-not $value) { return }
    $name = $name.Trim(); $value = $value.Trim()
    [Environment]::SetEnvironmentVariable($name,$value,'Process')
  }
}

function Wait-Ok([string]$url, [int]$tries=20) {
  for ($i=1; $i -le $tries; $i++) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing -Uri $url -Method GET -TimeoutSec 5
      if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    Start-Sleep -Seconds 1
  }
  return $false
}

Write-Host "Loading .env.local if present" -ForegroundColor Cyan
Load-EnvFile "$ROOT\.env.local"

# Ensure httpx is available in venv (used by chat shim)
try {
  & $VENV_PY -c "import httpx" 2>$null
} catch {
  Write-Host "Installing httpx into venv" -ForegroundColor Yellow
  & $VENV_PY -m pip install --quiet httpx
}

# 1) Start ODIA TTS if not healthy
if (-not (Wait-Ok "http://localhost:8002/health")) {
  Write-Host "Starting ODIA TTS (8002)..." -ForegroundColor Green
  Start-Process -WindowStyle Minimized `
    -FilePath $VENV_PY `
    -ArgumentList @("-m","uvicorn","odia_voice_api:app","--app-dir",$ROOT,"--host","0.0.0.0","--port","8002","--reload") `
    -WorkingDirectory $ROOT
  if (-not (Wait-Ok "http://localhost:8002/health")) { throw "TTS failed to start" }
} else {
  Write-Host "ODIA TTS already healthy." -ForegroundColor Green
}

# 2) Start chat shim (8003)
if (-not (Wait-Ok "http://localhost:8003/health")) {
  Write-Host "Starting chat shim (8003)..." -ForegroundColor Green
  Start-Process -WindowStyle Minimized `
    -FilePath $VENV_PY `
    -ArgumentList @("$ROOT\chat_shim.py") `
    -WorkingDirectory $ROOT
  if (-not (Wait-Ok "http://localhost:8003/health")) { throw "Chat shim failed to start" }
} else {
  Write-Host "Chat shim already healthy." -ForegroundColor Green
}

# 3) Serve the UI
Write-Host "Starting UI on http://localhost:$UiPort " -ForegroundColor Green
Start-Process -WindowStyle Minimized powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$ROOT\ui\serve-ui.ps1`" -Port $UiPort"

Start-Sleep -Seconds 1
Start-Process "http://localhost:$UiPort"
Write-Host "All set. Type in the page and Lexi will speak back." -ForegroundColor Cyan
