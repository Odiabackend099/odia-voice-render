# Check TTS is healthy
Invoke-RestMethod http://localhost:8002/health

# Synthesize using your reference voice (no named speaker)
$body = @{
  text        = "How you dey? We don ready to run am!"
  agent       = "lexi"
  language    = "en"
  speed       = 1.0
  speaker_wav = "C:\Users\OD~IA\ODIA-VOICE\ref\lexi_ref.wav"
} | ConvertTo-Json

$r = Invoke-RestMethod -Method POST -Uri http://localhost:8002/speak -ContentType application/json -Body $body
Invoke-WebRequest -OutFile "$env:USERPROFILE\Desktop\demo.wav" -Uri ("http://localhost:8002" + $r.audio_url)
"Saved => $env:USERPROFILE\Desktop\demo.wav"
