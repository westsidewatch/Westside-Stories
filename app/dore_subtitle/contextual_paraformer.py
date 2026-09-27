"""Out-of-process Chinese contextual ASR using upstream FunASR.

FunASR owns recognition, VAD, punctuation and contextual hotwords. The worker
normalizes upstream sentence/timestamp output into the segment contract already
used by Westside Stories, so it can be promoted directly to production without
keeping model memory resident in the GUI process.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .dynamic_context import DynamicTerm, hotword_string


@dataclass(frozen=True)
class ChallengerResult:
    ok: bool
    text: str
    raw: dict
    error: str = ""


WORKER = r'''import json, sys
from funasr import AutoModel

audio, hotwords = sys.argv[1], sys.argv[2]
model = AutoModel(
    model="paraformer-zh",
    vad_model="fsmn-vad",
    punc_model="ct-punc",
    disable_update=True,
)
kwargs = {"input": audio, "batch_size_s": 300}
if hotwords.strip():
    kwargs["hotword"] = hotwords
result = model.generate(**kwargs)
print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
'''


def _items(payload: dict) -> list[dict]:
    result = payload.get("result") or []
    if isinstance(result, dict):
        result = [result]
    return [item for item in result if isinstance(item, dict)]


def _extract_text(payload: dict) -> str:
    return "".join(str(item.get("text") or "").strip() for item in _items(payload)).strip()


def _normalize_segments(payload: dict) -> list[dict]:
    """Convert FunASR sentence/timestamp metadata to Westside SRT segments."""
    segments: list[dict] = []
    for item in _items(payload):
        sentence_info = item.get("sentence_info") or item.get("sentences") or []
        for sentence in sentence_info:
            if not isinstance(sentence, dict):
                continue
            text = str(sentence.get("text") or "").strip()
            start = sentence.get("start")
            end = sentence.get("end")
            if text and start is not None and end is not None:
                # FunASR sentence timestamps are milliseconds.
                segments.append({"start": float(start) / 1000.0, "end": float(end) / 1000.0, "text": text})
        if sentence_info:
            continue

        stamps = item.get("timestamp") or []
        text = str(item.get("text") or "").strip()
        if text and stamps:
            valid = [stamp for stamp in stamps if isinstance(stamp, (list, tuple)) and len(stamp) >= 2]
            if valid:
                segments.append({"start": float(valid[0][0]) / 1000.0, "end": float(valid[-1][1]) / 1000.0, "text": text})
    return segments


def transcribe_challenger(
    python_executable: str,
    audio: Path,
    context: Iterable[DynamicTerm] = (),
    timeout: int = 3600,
) -> ChallengerResult:
    """Run FunASR out-of-process; process exit releases model memory."""
    hotwords = hotword_string(context)
    try:
        proc = subprocess.run(
            [python_executable, "-c", WORKER, str(audio), hotwords],
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except Exception as exc:
        return ChallengerResult(False, "", {}, f"{type(exc).__name__}: {exc}")

    if proc.returncode != 0:
        return ChallengerResult(False, "", {}, (proc.stderr or proc.stdout or "ASR failed").strip())

    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        return ChallengerResult(False, "", {}, "ASR returned no result")
    try:
        payload = json.loads(lines[-1])
    except Exception as exc:
        return ChallengerResult(False, "", {}, f"invalid ASR output: {exc}")

    text = _extract_text(payload)
    segments = _normalize_segments(payload)
    payload["text"] = text
    payload["segments"] = segments
    if not text:
        return ChallengerResult(False, "", payload, "ASR returned empty text")
    return ChallengerResult(True, text, payload)
