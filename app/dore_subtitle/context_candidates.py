"""Bounded context candidate generation for Doré Subtitle Pack v2.

Context is allowed to propose candidates only for already-suspicious evidence.
It never edits subtitle text and never treats dictionary membership as proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from .evidence_packet import EvidencePacket
from .suspicion_gate import Suspicion


@dataclass(frozen=True)
class ContextTerm:
    text: str
    category: str
    weight: float = 1.0
    source: str = "local-pack"


@dataclass(frozen=True)
class Candidate:
    segment_id: str
    observed: str
    proposed: str
    category: str
    lexical_similarity: float
    context_weight: float
    source: str
    authority: str = "candidate-only"


@dataclass(frozen=True)
class CandidatePolicy:
    minimum_similarity: float = 0.55
    maximum_candidates: int = 5


def _windows(text: str, target_len: int) -> Iterable[str]:
    if not text or target_len <= 0:
        return ()
    low = max(1, target_len - 1)
    high = min(len(text), target_len + 1)
    return (
        text[start:start + size]
        for size in range(low, high + 1)
        for start in range(0, len(text) - size + 1)
    )


def propose(
    packet: EvidencePacket,
    suspicion: Suspicion,
    terms: Iterable[ContextTerm],
    policy: CandidatePolicy | None = None,
) -> list[Candidate]:
    """Return ranked candidates only when Suspicion Gate already fired."""
    if not suspicion.suspicious or suspicion.segment_id != packet.segment_id:
        return []

    policy = policy or CandidatePolicy()
    text = packet.original_text.strip()
    if not text:
        return []

    ranked: list[Candidate] = []
    seen: set[tuple[str, str]] = set()
    for term in terms:
        proposed = term.text.strip()
        if not proposed or proposed in text:
            continue
        best_observed = ""
        best_score = 0.0
        for observed in _windows(text, len(proposed)):
            score = SequenceMatcher(None, observed, proposed).ratio()
            if score > best_score:
                best_observed, best_score = observed, score
        if best_score < policy.minimum_similarity:
            continue
        key = (best_observed, proposed)
        if key in seen:
            continue
        seen.add(key)
        ranked.append(Candidate(
            segment_id=packet.segment_id,
            observed=best_observed,
            proposed=proposed,
            category=term.category,
            lexical_similarity=round(best_score, 4),
            context_weight=float(term.weight),
            source=term.source,
        ))

    ranked.sort(key=lambda item: (item.lexical_similarity * item.context_weight), reverse=True)
    return ranked[:policy.maximum_candidates]
