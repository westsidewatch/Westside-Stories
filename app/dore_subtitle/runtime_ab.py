"""Evaluate the most recent real-audio Whisper/Contextual-ASR pair.

Promotion requires a human-verified reference transcript. Runtime evidence is
never promoted from synthetic examples or from the challenger's own output.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .asr_benchmark import BenchmarkCase, decide


def evaluate_runtime_pair(
    *,
    whisper_text: str,
    challenger_text: str,
    reference_text: str,
    domain_terms: Iterable[str] = (),
    case_id: str = "real-audio",
) -> dict:
    if not reference_text.strip():
        raise ValueError("human-verified reference transcript is required")
    if not whisper_text.strip() or not challenger_text.strip():
        raise ValueError("both real ASR outputs are required")
    decision = decide((BenchmarkCase(
        case_id=case_id,
        reference=reference_text,
        baseline=whisper_text,
        challenger=challenger_text,
        domain_terms=tuple(domain_terms),
    ),))
    return {
        "schema": "westside.asr-ab.v1",
        "case_id": case_id,
        "promoted": decision.promoted,
        "reason": decision.reason,
        "baseline": asdict(decision.baseline),
        "challenger": asdict(decision.challenger),
    }


def evaluate_saved_job(app_home: Path, reference_path: Path, domain_terms: Iterable[str] = ()) -> dict:
    original = app_home / "dore" / "last_result.whisper-original.srt"
    challenger = app_home / "dore" / "last_result.contextual-asr.json"
    if not original.exists():
        raise FileNotFoundError(original)
    if not challenger.exists():
        raise FileNotFoundError(challenger)
    payload = json.loads(challenger.read_text(encoding="utf-8"))
    if not payload.get("ok"):
        raise RuntimeError("saved contextual ASR run was not successful")
    report = evaluate_runtime_pair(
        whisper_text=original.read_text(encoding="utf-8"),
        challenger_text=str(payload.get("text") or ""),
        reference_text=reference_path.read_text(encoding="utf-8"),
        domain_terms=domain_terms,
        case_id=reference_path.name,
    )
    output = app_home / "dore" / "last_result.asr-ab.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
