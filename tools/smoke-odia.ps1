$ErrorActionPreference = 'SilentlyContinue'
$TTS  = 'http://localhost:8002'
$REF  = 'C:\Users\OD~IA\ODIA-VOICE\ref\lexi_ref.wav'
$OUT  = 'C:\Users\OD~IA\ODIA-VOICE\demo_smoke.wav'

Write-Host "🩺 ODIA Smoke Test" -ForegroundColor Cyan

# 1) Health check
try {
  $h = Invoke-RestMethod "http://localhost:8002/health" -TimeoutSec 8
  if (-not $h) { throw "No health payload" }
  Write-Host "✅ API up: " -ForegroundColor Green
} catch {
  Write-Host "❌ Can't reach http://localhost:8002/health — start the API first (use 'Start ODIA')." -ForegroundColor Red
  pause; exit 1
}

# 2) Make Lexi speak using your local reference voice
if (!(Test-Path $REF)) {
  Write-Host "⚠️ Reference voice not found at $REF" -ForegroundColor Yellow
  Write-Host "   Put a WAV there or update the path in this script." -ForegroundColor Yellow
}

$body = @{
  text        = "How you dey? We don ready to run am!"
  language    = "en"
  agent       = "lexi"
  speaker_wav = $REF
} | ConvertTo-Json

try {
  $r = Invoke-RestMethod -Method POST -Uri "http://localhost:8002/speak" -ContentType application/json -Body $body -TimeoutSec 60
  if (-not $r.audio_url) { throw "No audio_url in response: " }
  $src = "http://localhost:8002$($r.audio_url)"
  Invoke-WebRequest -OutFile $OUT -Uri $src -TimeoutSec 60 | Out-Null
  if (Test-Path $OUT) {
    Write-Host "✅ Voice saved => $OUT" -ForegroundColor Green
    Start-Process $OUT
  } else {
    throw "Audio file not found after download."
  }
} catch {
  Write-Host "❌ Smoke test failed: $(.Exception.Message)" -ForegroundColor Red
}

