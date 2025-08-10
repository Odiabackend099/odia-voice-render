import os, asyncio, json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

ODIA_TTS_URL = os.getenv("ODIA_TTS_URL", "http://localhost:8002")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
PORT = int(os.getenv("CHAT_SHIM_PORT", "8003"))

app = FastAPI(title="ODIA Chat Shim", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatIn(BaseModel):
    text: str

class ChatOut(BaseModel):
    reply_text: str
    audio_url: str

@app.get("/health")
async def health():
    return {"status":"ok","tts":ODIA_TTS_URL}

async def think(text: str) -> str:
    # If no Claude key, fallback reply
    if not CLAUDE_API_KEY:
        return f"Thanks. I understand: {text}"

    # Claude API call (Messages)
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 256,
        "messages": [
            {"role":"user","content": text}
        ],
        "system": "You are Lexi, a friendly Nigerian voice agent. Be concise and warm."
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            # data.content is a list of blocks; take first text
            blocks = data.get("content", [])
            for b in blocks:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text"):
                    return b["text"]
            return "Alright. How can I help you?"
    except Exception:
        # silent fallback
        return f"Okay. I got: {text}"

@app.post("/chat/lexi", response_model=ChatOut)
async def chat_lexi(payload: ChatIn):
    user_text = payload.text.strip()
    if not user_text:
        raise HTTPException(400, "Empty text")

    reply_text = await think(user_text)

    # Ask ODIA TTS to speak the reply
    tts_body = {
        "text": reply_text,
        "agent": "lexi",
        "language": "en",
        "speed": 1.0
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{ODIA_TTS_URL}/speak", json=tts_body)
        if r.status_code != 200:
            raise HTTPException(500, f"TTS failed: {r.text}")
        data = r.json()
        audio_url = data.get("audio_url","")
        if audio_url and not audio_url.startswith("http"):
            audio_url = f"{ODIA_TTS_URL}{audio_url}"
        return ChatOut(reply_text=reply_text, audio_url=audio_url)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("chat_shim:app", host="0.0.0.0", port=PORT, reload=False)
