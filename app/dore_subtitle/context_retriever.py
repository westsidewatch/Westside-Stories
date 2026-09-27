"""Evidence-backed retrieval for per-job ASR context.

This module does not contain a static church vocabulary. It reads confirmed
local memory plus optional corpus evidence supplied for the current job, ranks
only terms relevant to the current scope/query, and returns a bounded pack for
model-level contextual biasing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .dynamic_context import DynamicTerm, build_dynamic_context
from .local_memory import MemoryScope, applicable_terms, load_memory

_TOKEN = re.compile(r"[\w\u3400-\u9fff]+", re.UNICODE)


@dataclass(frozen=True)
class CorpusTerm:
    text: str
    evidence: str = ""
    weight: float = 1.0


def _query_tokens(text: str) -> set[str]:
    return {token for token in _TOKEN.findall(text or "") if len(token) >= 2}


def _relevance(term: CorpusTerm, query: str) -> float:
    text = term.text.strip()
    if not text:
        return 0.0
    haystack = f"{text} {term.evidence}".strip()
    tokens = _query_tokens(query)
    overlap = sum(1 for token in tokens if token in haystack)
    exact = 1.0 if text in query else 0.0
    return max(0.0, term.weight) * (1.0 + 0.35 * overlap + 0.75 * exact)


def retrieve_context(
    *,
    scope: MemoryScope,
    memory_path: Path | None = None,
    corpus_terms: Iterable[CorpusTerm] = (),
    query: str = "",
    limit: int = 64,
) -> list[DynamicTerm]:
    learned: list[str] = []
    if memory_path is not None and memory_path.exists():
        memory = applicable_terms(load_memory(memory_path), scope)
        memory.sort(key=lambda item: (-item.confirmations, item.confirmed))
        learned = [item.confirmed for item in memory if item.confirmed.strip()]

    ranked_corpus = sorted(
        ((item, _relevance(item, query)) for item in corpus_terms),
        key=lambda pair: (-pair[1], pair[0].text),
    )
    retrieved = [item.text for item, score in ranked_corpus if score > 0]

    return build_dynamic_context(
        scope,
        learned_terms=learned,
        retrieved_terms=retrieved,
        limit=limit,
    )
