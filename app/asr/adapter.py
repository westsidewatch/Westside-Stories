"""Stable ASR boundary for Westside Stories.

The product depends on this contract, not on a specific recognizer. MLX Whisper
remains the current/default backend. Recognition context is advisory: a backend
may consume supported hints or safely ignore them without blocking transcription.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class RecognitionHint:
    text: str
    weight: float = 1.0
    source: str = "local"
    category: str = "unknown"


@dataclass(frozen=True)
class TranscriptionRequest:
    audio_path: Path
    language: str | None = None
    recognition_hints: tuple[RecognitionHint, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TranscriptionResult:
    backend: str
    raw: dict[str, Any]
    hints_requested: int = 0
    hints_consumed: int = 0


class ASRAdapter(Protocol):
    name: str

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        ...
