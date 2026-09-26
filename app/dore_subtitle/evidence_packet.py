"""Immutable evidence packets for Doré Subtitle Gate v2.

Doré receives evidence; it does not own the ASR transcript.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA = "dore.subtitle-evidence.v2"

@dataclass(frozen=True)
class WordEvidence:
    text: str
    start: float | None = None
    end: float | None = None
    probability: float | None = None

@dataclass(frozen=True)
class EvidencePacket:
    segment_id: str
    original_text: str
    start: float
    end: float
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None
    words: tuple[WordEvidence, ...] = field(default_factory=tuple)
    previous_text: str = ""
    next_text: str = ""
    context_tags: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, **asdict(self)}
