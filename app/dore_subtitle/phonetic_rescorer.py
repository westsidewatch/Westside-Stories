"""Chinese phonetic candidate generation and contextual rescoring.

Candidates come only from the current Dynamic Context pack. There is no global
replacement dictionary. Pinyin is used when available; the module degrades
safely when the optional dependency is absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from .dynamic_context import DynamicTerm

try:
    from pypinyin import Style, lazy_pinyin
except Exception:  # optional until challenger runtime is installed
    Style = None
    lazy_pinyin = None


@dataclass(frozen=True)
class PhoneticCandidate:
    observed: str
    candidate: str
    phonetic_similarity: float
    context_score: float
    total_score: float
    source: str


def _phonetic_key(text: str) -> str:
    if lazy_pinyin is None:
        return ""
    syllables = lazy_pinyin(text, style=Style.NORMAL, errors="ignore")
    return " ".join(syllables).lower().strip()


def _similarity(a: str, b: str) -> float:
    pa, pb = _phonetic_key(a), _phonetic_key(b)
    if not pa or not pb:
        return 0.0
    return SequenceMatcher(None, pa, pb).ratio()


def candidates_for_span(
    observed: str,
    context: Iterable[DynamicTerm],
    *,
    minimum_phonetic_similarity: float = 0.72,
    limit: int = 8,
) -> list[PhoneticCandidate]:
    """Rank current-context terms that sound like an observed ASR span."""
    ranked: list[PhoneticCandidate] = []
    for term in context:
        if not term.text or term.text == observed:
            continue
        similarity = _similarity(observed, term.text)
        if similarity < minimum_phonetic_similarity:
            continue
        context_score = max(0.0, min(1.0, term.score))
        total = 0.68 * similarity + 0.32 * context_score
        ranked.append(PhoneticCandidate(
            observed=observed,
            candidate=term.text,
            phonetic_similarity=similarity,
            context_score=context_score,
            total_score=total,
            source=term.source,
        ))
    ranked.sort(key=lambda item: (-item.total_score, -item.phonetic_similarity, item.candidate))
    return ranked[:max(0, limit)]


def best_candidate(
    observed: str,
    context: Iterable[DynamicTerm],
    *,
    minimum_total_score: float = 0.84,
) -> PhoneticCandidate | None:
    """Return evidence only; callers decide whether a transcript may change."""
    ranked = candidates_for_span(observed, context)
    if not ranked or ranked[0].total_score < minimum_total_score:
        return None
    return ranked[0]
