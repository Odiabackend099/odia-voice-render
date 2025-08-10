$body = @{
  text        = "How you dey? We don ready to run am!"
  speaker_wav = "C:\Users\OD~IA\ODIA-VOICE\ref\lexi_ref.wav"
} | ConvertTo-Json

$r = Invoke-RestMethod -Method POST -Uri http://localhost:8002/speak -ContentType application/json -Body $body
Invoke-WebRequest -OutFile "C:\Users\OD~IA\ODIA-VOICE\demo.wav" -Uri ("http://localhost:8002" + $r.audio_url)
Write-Host "✅ Saved => C:\Users\OD~IA\ODIA-VOICE\demo.wav"
