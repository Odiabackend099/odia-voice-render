from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse
from TTS.utils.synthesizer import Synthesizer
import uuid, os

CFG = r"C:\ODIA-VOICE\VOICEPACK_pidgin\config.json"
CKPT = r"C:\ODIA-VOICE\VOICEPACK_pidgin\best_model.pth"
OUT_DIR = r"C:\ODIA-VOICE\api_out"
os.makedirs(OUT_DIR, exist_ok=True)

synth = Synthesizer(tts_checkpoint=CKPT, tts_config_path=CFG, use_cuda=True)
app = FastAPI()

class Inp(BaseModel):
    text: str

@app.post("/speak")
def speak(inp: Inp):
    wav_path = os.path.join(OUT_DIR, f"{uuid.uuid4().hex}.wav")
    wav = synth.tts(inp.text)
    synth.save_wav(wav, wav_path)
    return {"path": wav_path}

@app.get("/file")
def file(path: str):
    return FileResponse(path, media_type="audio/wav")
