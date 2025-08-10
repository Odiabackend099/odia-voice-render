param(
  [Parameter(Mandatory=$false)][string]$Text = "Hello from ODIA",
  [Parameter(Mandatory=$false)][string]$Out
)

if (-not $Out -or [string]::IsNullOrWhiteSpace($Out)) {
  $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $Out = "C:\Users\OD~IA\ODIA-VOICE\out\$stamp.wav"
}

# Call local API
$body = @{ text = $Text } | ConvertTo-Json
$r = Invoke-RestMethod -Method POST -Uri http://localhost:8002/speak -ContentType application/json -Body $body

# Download WAV
Invoke-WebRequest -OutFile $Out -Uri ("http://localhost:8002" + $r.audio_url)
Write-Host "Saved => $Out"

# Try SoundPlayer
try {
  $player = New-Object System.Media.SoundPlayer $Out
  $player.Load()
  $player.PlaySync()
  return
} catch { Write-Host "SoundPlayer failed, trying Windows Media Player..." }

# Try Windows Media Player (if installed)
try {
  Start-Process -FilePath "wmplayer.exe" -ArgumentList "`"$Out`"" -WindowStyle Hidden | Out-Null
  return
} catch { Write-Host "WMP not available, opening the folder..." }

# Fallback: open the output folder so you can click the file
Start-Process "$([System.IO.Path]::GetDirectoryName($Out))"
