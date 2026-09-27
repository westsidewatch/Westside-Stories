"""Run one verified audio clip through the real baseline and challenger.

This is an evaluation path only. It does not switch production ASR. The two
recognizers run sequentially so their model memory is not intentionally held at
the same time by this harness.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from asr.adapter import TranscriptionRequest
from asr.mlx_whisper_adapter import MLXWhisperAdapter
from dore_subtitle.asr_benchmark import BenchmarkCase, BenchmarkDecision, decide
from dore_subtitle.contextual_paraformer import transcribe_challenger
from dore_subtitle.dynamic_context import DynamicTerm


@dataclass(frozen=True)
class LiveBenchmarkResult:
    baseline_text: str
    challenger_text: str
    decision: BenchmarkDecision


def _whisper_text(raw: dict) -> str:
    text = str(raw.get("text") or "").strip()
    if text:
        return text
    return "".join(
        str(segment.get("text") or "").strip()
        for segment in (raw.get("segments") or [])
        if isinstance(segment, dict)
    ).strip()


def run_verified_clip(
    audio: Path,
    reference: str,
    python_executable: str,
    context: Iterable[DynamicTerm] = (),
    domain_terms: Iterable[str] = (),
    language: str = "zh",
) -> LiveBenchmarkResult:
    """Transcribe real audio with both engines and apply the promotion gate."""
    if not audio.exists():
        raise FileNotFoundError(audio)
    if not reference.strip():
        raise ValueError("verified reference transcript is required")

    baseline_result = MLXWhisperAdapter().transcribe(
        TranscriptionRequest(audio_path=audio, language=language)
    )
    baseline_text = _whisper_text(baseline_result.raw)

    challenger_result = transcribe_challenger(
        python_executable=python_executable,
        audio=audio,
        context=tuple(context),
    )
    if not challenger_result.ok:
        raise RuntimeError(f"Contextual Paraformer failed: {challenger_result.error}")

    case = BenchmarkCase(
        case_id=audio.name,
        reference=reference,
        baseline=baseline_text,
        challenger=challenger_result.text,
        domain_terms=tuple(domain_terms),
    )
    decision = decide((case,))
    return LiveBenchmarkResult(baseline_text, challenger_result.text, decision)
