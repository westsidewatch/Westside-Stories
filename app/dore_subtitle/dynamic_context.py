"""Build small per-job context packs for model-level ASR biasing.

No global static church vocabulary is used. Context must come from current
scope, confirmed local memory, or retrieval evidence. The result is bounded so
runtime memory and decoder bias stay controlled.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from dore_subtitle.local_memory import MemoryScope


@dataclass(frozen=True)
class DynamicTerm:
    text: str
    score: float
    source: str


def build_dynamic_context(
    scope: MemoryScope,
    learned_terms: Iterable[str] = (),
    retrieved_terms: Iterable[str] = (),
    limit: int = 64,
) -> list[DynamicTerm]:
    ranked: dict[str, DynamicTerm] = {}

    def add(value: str, score: float, source: str) -> None:
        text = " ".join((value or "").strip().split())
        if len(text) < 2:
            return
        item = DynamicTerm(text, score, source)
        old = ranked.get(text)
        if old is None or item.score > old.score:
            ranked[text] = item

    add(scope.organisation, 1.00, "organisation")
    add(scope.speaker, 0.98, "speaker")
    add(scope.series, 0.96, "series")
    for term in learned_terms:
        add(term, 0.94, "local-memory")
    for term in retrieved_terms:
        add(term, 0.88, "retriever")

    return sorted(ranked.values(), key=lambda x: (-x.score, x.text))[:max(0, limit)]


def hotword_string(terms: Iterable[DynamicTerm]) -> str:
    return " ".join(term.text for term in terms if term.text)
