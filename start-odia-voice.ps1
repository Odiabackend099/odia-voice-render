$APPDIR = "C:\Users\OD~IA\ODIA-VOICE"
$PY = "C:\Users\OD~IA\odia-tts\Scripts\python.exe"
Get-Process python -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
& "$PY" -m uvicorn odia_voice_api:app --app-dir $APPDIR --reload-dir $APPDIR --host 0.0.0.0 --port 8002 --reload
