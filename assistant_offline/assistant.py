import json, time, tempfile, os, sys
from pathlib import Path
import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
import simpleaudio as sa
from faster_whisper import WhisperModel

ROOT = Path(__file__).parent
CFG  = json.load(open(ROOT/"config.json", "r", encoding="utf-8"))

VOICE_API   = CFG["voice_api_url"]
SPEAKER_WAV = CFG["speaker_wav"]

# ---- STT (offline) ----
# Tip: first run online once so faster-whisper caches the model locally,
# then it works offline (cache is under %LOCALAPPDATA%\faster-whisper).
print("Loading Whisper (base.en)…")
stt_model = WhisperModel("base.en", device="auto", compute_type="default")

def record_to_wav(tmp_path: Path, fs=16000, seconds=15):
    print("???  Speak now (max 15s)…")
    audio = sd.rec(int(seconds*fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    x = audio.flatten()
    thr = 0.01
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return False
    start = max(idx[0]-int(0.1*fs), 0)
    end = min(idx[-1]+int(0.2*fs), len(x))
    x = x[start:end]
    sf.write(tmp_path.as_posix(), x, fs)
    return True

def transcribe(wav_path: Path) -> str:
    segments, info = stt_model.transcribe(wav_path.as_posix(), language="en")
    return "".join([s.text for s in segments]).strip()

# ---- LLM (offline): Ollama or LM Studio ----
def ask_llm(user_text: str) -> str:
    if CFG["llm_backend"] == "lmstudio":
        url = CFG["lmstudio_url"]
        body = {
            "model": CFG["model"],
            "messages": [
                {"role":"system","content": CFG["system_prompt"]},
                {"role":"user","content": user_text}
            ],
            "temperature": 0.6
        }
        r = requests.post(url, json=body, timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    else:
        url = CFG["ollama_url"]
        body = {
            "model": CFG["model"],
            "stream": False,
            "messages":[
                {"role":"system","content": CFG["system_prompt"]},
                {"role":"user","content": user_text}
            ]
        }
        r = requests.post(url, json=body, timeout=180)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()

# ---- TTS: your local XTTS API (reference voice) ----
def speak(text: str):
    j = {"text": text, "speaker_wav": SPEAKER_WAV}
    r = requests.post(f"{VOICE_API}/speak", json=j, timeout=180)
    r.raise_for_status()
    audio_url = r.json()["audio_url"]
    wav = requests.get(f"{VOICE_API}{audio_url}", timeout=180)
    wav.raise_for_status()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(wav.content)
        tmp = f.name
    wave_obj = sa.WaveObject.from_wave_file(tmp)
    play_obj = wave_obj.play()
    play_obj.wait_done()
    os.unlink(tmp)

def need(path): 
    if not Path(path).exists():
        print(f"Missing path: {path}"); sys.exit(1)

def check_health():
    try:
        h = requests.get(f"{VOICE_API}/health", timeout=5).json()
        print("? Voice API:", h)
    except Exception as e:
        print("? Voice API not reachable:", e); sys.exit(1)
    need(SPEAKER_WAV)

def main():
    print("ODIA Offline Assistant")
    print("R = record mic, T = type text, Q = quit")
    check_health()
    while True:
        cmd = input("\n[R/T/Q] > ").strip().lower()
        if cmd == "q": break
        if cmd == "t":
            user = input("You: ").strip()
            if not user: continue
        elif cmd == "r":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                tmpwav = Path(f.name)
            if not record_to_wav(tmpwav):
                print("…heard nothing.")
                try: os.unlink(tmpwav)
                except: pass
                continue
            user = transcribe(tmpwav)
            os.unlink(tmpwav)
            print(f"You (stt): {user}")
            if not user: continue
        else:
            continue

        try:
            reply = ask_llm(user)
            print(f"Lexi: {reply}")
            speak(reply)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
