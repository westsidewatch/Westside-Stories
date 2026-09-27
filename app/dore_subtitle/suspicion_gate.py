"""Conservative suspicion gate for Doré Subtitle Pack v2.

This module does not correct transcript text. It only identifies evidence that
may justify later review. Missing evidence is never treated as an error.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .evidence_packet import EvidencePacket, WordEvidence


@dataclass(frozen=True)
class Suspicion:
    segment_id: str
    reasons: tuple[str, ...]
    word_indexes: tuple[int, ...] = ()

    @property
    def suspicious(self) -> bool:
        return bool(self.reasons or self.word_indexes)


@dataclass(frozen=True)
class SuspicionPolicy:
    # Conservative initial values. They select review candidates only; they do
    # not authorize corrections.
    low_avg_logprob: float = -0.85
    high_no_speech_prob: float = 0.60
    high_compression_ratio: float = 2.40
    low_word_probability: float = 0.45
    min_word_duration: float = 0.04
    max_word_duration: float = 3.00


def _word_is_suspicious(word: WordEvidence, policy: SuspicionPolicy) -> bool:
    if word.probability is not None and word.probability < policy.low_word_probability:
        return True
    if word.start is not None and word.end is not None:
        duration = word.end - word.start
        if duration < 0:
            return True
        if word.text.strip() and (duration < policy.min_word_duration or duration > policy.max_word_duration):
            return True
    return False


def inspect(packet: EvidencePacket, policy: SuspicionPolicy | None = None) -> Suspicion:
    policy = policy or SuspicionPolicy()
    reasons: list[str] = []

    if packet.avg_logprob is not None and packet.avg_logprob < policy.low_avg_logprob:
        reasons.append("low_avg_logprob")
    if packet.no_speech_prob is not None and packet.no_speech_prob > policy.high_no_speech_prob and packet.original_text.strip():
        reasons.append("speech_on_high_no_speech")
    if packet.compression_ratio is not None and packet.compression_ratio > policy.high_compression_ratio:
        reasons.append("high_compression_ratio")

    word_indexes = tuple(
        index for index, word in enumerate(packet.words)
        if _word_is_suspicious(word, policy)
    )
    if word_indexes:
        reasons.append("suspicious_word_evidence")

    return Suspicion(packet.segment_id, tuple(reasons), word_indexes)


def inspect_all(packets: Iterable[EvidencePacket], policy: SuspicionPolicy | None = None) -> list[Suspicion]:
    policy = policy or SuspicionPolicy()
    return [result for packet in packets if (result := inspect(packet, policy)).suspicious]
