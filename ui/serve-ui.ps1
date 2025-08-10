param(
  [int]$Port = 5173
)
$ErrorActionPreference = "Stop"

# Go to UI dir
Set-Location -Path "$PSScriptRoot"

# Kill any http.server already on that port
Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | ForEach-Object {
  try {
    $pid = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Id
    if($pid){ Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue }
  } catch {}
}

# Start server
Write-Host "Serving UI on http://localhost:$Port"
$py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
if(-not (Test-Path $py)){ $py = "python" }  # fallback to PATH / venv

Start-Process -WindowStyle Minimized -FilePath $py -ArgumentList "-m http.server $Port -b 127.0.0.1" -PassThru | Out-Null

# wait until alive
$ok=$false
for($i=0;$i -lt 30;$i++){
  Start-Sleep -Milliseconds 300
  try{
    Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$Port" -TimeoutSec 1 | Out-Null
    $ok=$true; break
  }catch{}
}
if($ok){ Start-Process "http://localhost:$Port" } else { Write-Warning "UI server failed to start." }
