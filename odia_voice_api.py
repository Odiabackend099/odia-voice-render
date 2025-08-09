from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from TTS.api import TTS
import os, uuid, torch, logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("odia-voice")

APP_NAME = "ODIA Voice Engine"
OUT_DIR  = r"C:\ODIA-VOICE\api_out"
os.makedirs(OUT_DIR, exist_ok=True)

app = FastAPI(title=APP_NAME)

# Load a strong multilingual model. GPU if available.
gpu_ok = torch.cuda.is_available()
try:
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", gpu=gpu_ok)
    log.info("XTTS v2 loaded (gpu=%s)", gpu_ok)
except Exception as e:
    log.exception("XTTS load failed, falling back to CPU LJSpeech: %s", e)
    tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", gpu=False)

class VoiceRequest(BaseModel):
    text: str
    agent: str = "lexi"       # just a tag you can use in logs
    language: str = "en"      # keep "en" for Nigerian English/Pidgin
    speed: float = 1.0

@app.get("/")
def root():
    return {"status":"ok","engine":APP_NAME,"gpu":torch.cuda.is_available()}

@app.get("/health")
def health():
    return {"ready":True,"model":str(getattr(tts, "model_name", "coqui_tts")), "gpu":torch.cuda.is_available()}

@app.post("/speak")
def speak(req: VoiceRequest):
    try:
        text = req.text.strip()
        if not text:
            raise HTTPException(400, "Empty text")

        # unique filename
        audio_id = f"{uuid.uuid4().hex}.wav"
        path = os.path.join(OUT_DIR, audio_id)

        # XTTS v2 path (preferred)
        if hasattr(tts, "tts_to_file"):
            tts.tts_to_file(
                text=text,
                file_path=path,
                language=req.language,
                speaker_wav=None,   # default voice
                speed=req.speed
            )
        else:
            # fallback models
            wav = tts.tts(text)
            tts.synthesizer.save_wav(wav, path)

        return {"status":"SUCCESS","audio_url":f"/audio/{audio_id}","agent":req.agent}
    except Exception as e:
        log.exception("speak error: %s", e)
        raise HTTPException(500, f"Voice generation failed: {e}")

@app.get("/audio/{filename}")
def audio(filename: str):
    p = os.path.join(OUT_DIR, filename)
    if not os.path.exists(p):
        raise HTTPException(404, "File not found")
    return FileResponse(p, media_type="audio/wav")
