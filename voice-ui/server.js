import "dotenv/config";
import express from "express";
import multer from "multer";
import fs from "fs";
import path from "path";
import fetch from "node-fetch";
import Anthropic from "anthropic";

const app = express();
const upload = multer({ dest: path.join(process.cwd(), "tmp") });

const PORT = process.env.PORT || 3001;
const TTS_URL = process.env.ODIA_TTS_URL || "http://localhost:8002";
const TTS_AGENT = process.env.ODIA_TTS_AGENT || "lexi";
const REF_WAV = process.env.ODIA_TTS_SPEAKER_WAV || "C:\\Users\\OD~IA\\ODIA-VOICE\\ref\\lexi_ref.wav";
const OPENAI_KEY = process.env.OPENAI_API_KEY || "";
const CLAUDE_KEY = process.env.ANTHROPIC_API_KEY || "";

app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));
app.use(express.static(path.join(process.cwd(), "ui")));

function mask(s) { return s ? s.slice(0,4) + "•••" : ""; }

// --- Simple reply generator: Claude -> fallback ---
async function generateReply(promptText) {
  if (CLAUDE_KEY) {
    const anthropic = new Anthropic({ apiKey: CLAUDE_KEY });
    const msg = await anthropic.messages.create({
      model: "claude-3-5-sonnet-20240620",
      max_tokens: 200,
      temperature: 0.3,
      system: "You are Lexi, a friendly Nigerian assistant. Be concise and helpful.",
      messages: [{ role: "user", content: promptText }]
    });
    const content = msg?.content?.[0]?.text || "I hear you. How can I help?";
    return content;
  }
  // Offline fallback if no Claude key
  return `You said: "${promptText}". I dey here for you. How I fit help?`;
}

// --- Speak via ODIA TTS ---
async function speakWithOdiaTTS(text) {
  const body = {
    text,
    language: "en",
    agent: TTS_AGENT,
    speaker_wav: REF_WAV
  };
  const r = await fetch(`${TTS_URL}/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`TTS error ${r.status}: ${t}`);
  }
  const json = await r.json();
  if (!json.audio_url) throw new Error("TTS returned no audio_url");
  return { audioUrl: `${TTS_URL}${json.audio_url}` };
}

// --- Optional STT with OpenAI Whisper (webm, wav, mp3) ---
async function transcribeWithOpenAI(filePath) {
  if (!OPENAI_KEY) return ""; // no cloud STT
  const form = new FormData();
  form.append("file", new Blob([fs.readFileSync(filePath)]), path.basename(filePath));
  form.append("model", "whisper-1");
  const r = await fetch("https://api.openai.com/v1/audio/transcriptions", {
    method: "POST",
    headers: { Authorization: `Bearer ${OPENAI_KEY}` },
    body: form
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(`STT error ${r.status}: ${t}`);
  }
  const j = await r.json();
  return j.text || "";
}

// --- Health (proxies ODIA TTS health for convenience) ---
app.get("/api/health", async (req, res) => {
  try {
    const r = await fetch(`${TTS_URL}/health`, { timeout: 5000 });
    const j = await r.json();
    res.json({ ok: true, tts: j });
  } catch (e) {
    res.json({ ok: false, error: String(e) });
  }
});

// --- Unified endpoint: JSON ({text}) OR multipart (audio) ---
app.post("/api/reply", upload.single("audio"), async (req, res) => {
  try {
    let userText = (req.body?.text || "").trim();

    // If audio uploaded and OpenAI key exists, transcribe
    if (!userText && req.file && OPENAI_KEY) {
      userText = (await transcribeWithOpenAI(req.file.path)).trim();
    }

    // If still no text, but browser sent a "fallback_text" (from Web Speech)
    if (!userText && req.body?.fallback_text) {
      userText = String(req.body.fallback_text).trim();
    }

    if (!userText) {
      return res.status(400).json({ ok: false, error: "No text found (provide text or audio)." });
    }

    const replyText = await generateReply(userText);
    const { audioUrl } = await speakWithOdiaTTS(replyText);
    res.json({ ok: true, text_in: userText, reply_text: replyText, audio_url: audioUrl });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  } finally {
    if (req.file) fs.unlink(req.file.path, () => {});
  }
});

// UI fallback route
app.get("*", (req, res) => res.sendFile(path.join(process.cwd(), "ui", "index.html")));

app.listen(PORT, () => {
  console.log(`ODIA Voice UI on http://localhost:${PORT}`);
  console.log(`TTS => ${TTS_URL} | Whisper: ${OPENAI_KEY ? "ON" : "OFF"} | Claude: ${CLAUDE_KEY ? "ON" : "OFF"}`);
});
