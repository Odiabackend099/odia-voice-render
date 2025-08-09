import csv, pathlib, sys
from faster_whisper import WhisperModel

SEG = pathlib.Path(r"C:\ODIA-VOICE\wavs_seg")
META = pathlib.Path(r"C:\ODIA-VOICE\metadata.csv")

MODEL = "medium"
if len(sys.argv) > 1 and sys.argv[1] in {"tiny","base","small","medium","large-v3"}:
    MODEL = sys.argv[1]

print("Loading Whisper model:", MODEL)
model = WhisperModel(MODEL, device="cuda", compute_type="float16")

rows = []
files = sorted(SEG.glob("*.wav"))
print("Found clips:", len(files))
for f in files:
    segments, _ = model.transcribe(str(f), language="en", vad_filter=True)
    text = " ".join(s.text.strip() for s in segments).strip()
    if text:
        rows.append((f.name, text))

META.parent.mkdir(parents=True, exist_ok=True)
with META.open("w", newline="", encoding="utf-8") as fp:
    w = csv.writer(fp, delimiter="|")
    w.writerows(rows)

print("Wrote", META, "rows:", len(rows))
