#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

URL="${1:-https://youtu.be/Z0L3jXp7h-U}"
VIDEO_ID="$(python3 - "$URL" <<'PY'
import sys
from urllib.parse import urlparse, parse_qs
url=sys.argv[1]
p=urlparse(url)
if p.netloc in {"youtu.be", "www.youtu.be"}:
    video_id=p.path.strip("/").split("/")[0]
elif "youtube.com" in p.netloc:
    video_id=parse_qs(p.query).get("v", [""])[0]
else:
    video_id=url.strip()
if not video_id:
    raise SystemExit("Could not parse YouTube video ID")
print(video_id)
PY
)"
OUT=".benchmark-real/${VIDEO_ID}"
mkdir -p "$OUT"

if [ -x "/opt/homebrew/bin/python3" ]; then PY="/opt/homebrew/bin/python3"; else PY="$(command -v python3)"; fi
VENV=".benchmark-real/venv"
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
VPY="$VENV/bin/python"
"$VPY" -m pip install -q --upgrade pip yt-dlp mlx-whisper funasr pypinyin

"$VPY" -m yt_dlp -x --audio-format wav -o "$OUT/source.%(ext)s" "$URL"
AUDIO="$OUT/source.wav"

PYTHONPATH="app" "$VPY" - "$AUDIO" "$OUT" "$VIDEO_ID" <<'PY'
import json, sys
from pathlib import Path
from asr.adapter import TranscriptionRequest
from asr.mlx_whisper_adapter import MLXWhisperAdapter
from dore_subtitle.context_retriever import retrieve_context
from dore_subtitle.contextual_paraformer import transcribe_challenger
from dore_subtitle.local_memory import MemoryScope

audio=Path(sys.argv[1]); out=Path(sys.argv[2]); video_id=sys.argv[3]
scope=MemoryScope("Living Water West", "", "")
context=retrieve_context(scope=scope, query="中文教會講道")
base=MLXWhisperAdapter().transcribe(TranscriptionRequest(audio_path=audio, language="zh"))
base_text=str(base.raw.get("text") or "").strip()
challenger=transcribe_challenger(sys.executable, audio, context=context)
(out/"whisper.txt").write_text(base_text, encoding="utf-8")
(out/"contextual.txt").write_text(challenger.text if challenger.ok else "", encoding="utf-8")
(out/"evidence.json").write_text(json.dumps({
 "source":video_id,
 "challenger_ok":challenger.ok,
 "challenger_error":challenger.error,
 "context":[{"text":x.text,"score":x.score,"source":x.source} for x in context],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("REAL A/B OUTPUT", video_id)
print("Whisper:", base_text)
print("Contextual:", challenger.text if challenger.ok else challenger.error)
PY

echo "Evidence: $OUT/whisper.txt $OUT/contextual.txt $OUT/evidence.json"
