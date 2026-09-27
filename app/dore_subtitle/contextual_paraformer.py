"""Isolated Chinese contextual-ASR challenger.

The production Whisper path is untouched. This adapter is invoked as a short-
lived subprocess by the benchmark/challenger layer, so FunASR does not become a
resident dependency of the GUI process. Dynamic context is passed as model-level
hotwords; there is no post-hoc replacement table here.
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


def _extract_text(payload: dict) -> str:
    result = payload.get("result") or []
    if isinstance(result, dict):
        result = [result]
    parts: list[str] = []
    for item in result:
        if isinstance(item, dict) and item.get("text"):
            parts.append(str(item["text"]).strip())
    return "".join(parts).strip()


def transcribe_challenger(
    python_executable: str,
    audio: Path,
    context: Iterable[DynamicTerm] = (),
    timeout: int = 3600,
) -> ChallengerResult:
    """Run FunASR out-of-process and release its model memory on process exit."""
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
        return ChallengerResult(False, "", {}, (proc.stderr or proc.stdout or "challenger failed").strip())

    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        return ChallengerResult(False, "", {}, "challenger returned no result")
    try:
        payload = json.loads(lines[-1])
    except Exception as exc:
        return ChallengerResult(False, "", {}, f"invalid challenger output: {exc}")
    return ChallengerResult(True, _extract_text(payload), payload)
