#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

URL="${1:-https://youtu.be/Z0L3jXp7h-U}"
OUT=".benchmark-real"
mkdir -p "$OUT"

if [ -x "/opt/homebrew/bin/python3" ]; then PY="/opt/homebrew/bin/python3"; else PY="$(command -v python3)"; fi
VENV="$OUT/venv"
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
VPY="$VENV/bin/python"
"$VPY" -m pip install -q --upgrade pip yt-dlp mlx-whisper funasr pypinyin

"$VPY" -m yt_dlp -x --audio-format wav -o "$OUT/source.%(ext)s" "$URL"
AUDIO="$OUT/source.wav"

PYTHONPATH="app" "$VPY" - "$AUDIO" "$OUT" <<'PY'
import json, sys
from pathlib import Path
from asr.adapter import TranscriptionRequest
from asr.mlx_whisper_adapter import MLXWhisperAdapter
from dore_subtitle.context_retriever import CorpusTerm, retrieve_context
from dore_subtitle.contextual_paraformer import transcribe_challenger
from dore_subtitle.local_memory import MemoryScope

audio=Path(sys.argv[1]); out=Path(sys.argv[2])
scope=MemoryScope("Living Water West", "", "")
# These are benchmark annotations supplied by the user for this specific real sermon,
# not product replacement rules. They enter only as contextual evidence.
corpus=[
    CorpusTerm("慕道", "本測試講道包含慕道相關語境", 1.0),
    CorpusTerm("錫安", "本測試講道包含錫安相關語境", 1.0),
    CorpusTerm("恩召", "本測試講道包含恩召相關語境", 1.0),
]
context=retrieve_context(scope=scope, corpus_terms=corpus, query="中文教會講道 慕道 錫安 恩召")
base=MLXWhisperAdapter().transcribe(TranscriptionRequest(audio_path=audio, language="zh"))
base_text=str(base.raw.get("text") or "").strip()
challenger=transcribe_challenger(sys.executable, audio, context=context)
(out/"whisper.txt").write_text(base_text, encoding="utf-8")
(out/"contextual.txt").write_text(challenger.text if challenger.ok else "", encoding="utf-8")
(out/"evidence.json").write_text(json.dumps({
 "source":"Z0L3jXp7h-U",
 "challenger_ok":challenger.ok,
 "challenger_error":challenger.error,
 "context":[{"text":x.text,"score":x.score,"source":x.source} for x in context],
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("REAL A/B OUTPUT")
print("Whisper:", base_text)
print("Contextual:", challenger.text if challenger.ok else challenger.error)
PY

echo "Evidence: $OUT/whisper.txt $OUT/contextual.txt $OUT/evidence.json"
