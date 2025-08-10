from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os, hashlib
import soundfile as sf
import numpy as np

# Coqui TTS (XTTS v2)
from TTS.api import TTS

APP_DIR   = r"C:\Users\OD~IA\ODIA-VOICE"
OUT_DIR   = os.path.join(APP_DIR, "output")
REF_DIR   = os.path.join(APP_DIR, "ref")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(REF_DIR, exist_ok=True)

app = FastAPI(title="ODIA Voice API (ref-only)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceRequest(BaseModel):
    text: str
    language: str = "en"
    speed: float = 1.0
    agent: Optional[str] = "lexi"
    speaker_wav: Optional[str] = None

class VoiceResponse(BaseModel):
    status: str
    message: str
    audio_url: str
    agent: str
    cache_hit: bool
    processing_time_ms: int

# Load XTTS v2 once
tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

def cache_key(req: VoiceRequest, ref_path: str) -> str:
    s = f"{req.text}|{req.language}|{req.speed}|{req.agent}|{ref_path}"
    return hashlib.md5(s.encode()).hexdigest()

def pick_reference(req: VoiceRequest) -> str:
    # explicit wins
    if req.speaker_wav and os.path.exists(req.speaker_wav):
        return req.speaker_wav
    # default per agent
    defaults = {
        "lexi":  os.path.join(REF_DIR, "lexi_ref.wav"),
        "miss":  os.path.join(REF_DIR, "miss_ref.wav"),
        "atlas": os.path.join(REF_DIR, "atlas_ref.wav"),
        "legal": os.path.join(REF_DIR, "legal_ref.wav"),
    }
    agent = (req.agent or "lexi").lower()
    ref = defaults.get(agent, defaults["lexi"])
    if not os.path.exists(ref):
        raise HTTPException(
            status_code=400,
            detail=f"Missing reference voice file: {ref}. Put a WAV there or pass speaker_wav."
        )
    return ref

@app.get("/health")
def health():
    return {"ready": True, "model": "xtts_v2", "ref_dir": REF_DIR}

@app.get("/audio/{key}")
def get_audio(key: str):
    path = os.path.join(OUT_DIR, f"{key}.wav")
    if not os.path.exists(path):
        raise HTTPException(404, "Audio not found")
    return FileResponse(path, media_type="audio/wav")

@app.post("/speak", response_model=VoiceResponse)
def speak(req: VoiceRequest):
    ref = pick_reference(req)
    key = cache_key(req, ref)
    out_path = os.path.join(OUT_DIR, f"{key}.wav")
    if os.path.exists(out_path):
        return VoiceResponse(
            status="SUCCESS",
            message="cache",
            audio_url=f"/audio/{key}",
            agent=req.agent or "lexi",
            cache_hit=True,
            processing_time_ms=0,
        )

    # XTTS reference-only call
    audio = tts_model.tts(text=req.text, speaker_wav=ref, language=req.language)
    # Coqui returns float32 numpy with sample rate 22050
    sf.write(out_path, np.array(audio, dtype=np.float32), 22050)

    return VoiceResponse(
        status="SUCCESS",
        message="ok",
        audio_url=f"/audio/{key}",
        agent=req.agent or "lexi",
        cache_hit=False,
        processing_time_ms=1
    )

# Optional: very small chat endpoint that just echoes then speaks (no cloud)
class ChatIn(BaseModel):
    text: str
    agent: Optional[str] = "lexi"
    speaker_wav: Optional[str] = None

class ChatOut(BaseModel):
    reply_text: str
    audio_url: str

@app.post("/chat/lexi", response_model=ChatOut)
def chat_lexi(inp: ChatIn):
    # offline fallback reply; you can wire Claude later
    reply = "I hear you. " + inp.text
    req = VoiceRequest(text=reply, agent=inp.agent, speaker_wav=inp.speaker_wav)
    res = speak(req)
    return ChatOut(reply_text=reply, audio_url=res.audio_url)
