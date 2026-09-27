"""Resolve local knowledge into bounded recognition and correction contexts.

The resolver keeps user-owned memory separate from the versioned Doré core.
Recognition hints are prepared before ASR; correction terms are consumed only
after the Suspicion Gate. Neither output authorizes transcript mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .context_candidates import ContextTerm
from .local_memory import LearnedTerm, MemoryScope, applicable_terms


@dataclass(frozen=True)
class RecognitionHint:
    text: str
    weight: float
    source: str
    category: str


@dataclass(frozen=True)
class ResolvedContext:
    recognition: tuple[RecognitionHint, ...]
    correction: tuple[ContextTerm, ...]


@dataclass(frozen=True)
class ResolverPolicy:
    max_recognition_hints: int = 48
    max_correction_terms: int = 96
    confirmation_step: float = 0.15
    max_local_weight: float = 2.5


def _local_weight(confirmations: int, policy: ResolverPolicy) -> float:
    return min(policy.max_local_weight, 1.0 + max(0, confirmations - 1) * policy.confirmation_step)


def resolve(
    *,
    scope: MemoryScope,
    local_memory: Iterable[LearnedTerm],
    core_terms: Iterable[ContextTerm] = (),
    session_terms: Iterable[ContextTerm] = (),
    policy: ResolverPolicy | None = None,
) -> ResolvedContext:
    """Build two bounded views of context without merging their authority.

    Local confirmed memory gets the strongest relevance inside its own scope.
    Session terms are temporary and never become memory automatically. Core
    terms remain generic fallbacks. Duplicate text keeps the strongest weight.
    """
    policy = policy or ResolverPolicy()
    local = applicable_terms(local_memory, scope)

    recognition_by_text: dict[str, RecognitionHint] = {}
    correction_by_text: dict[str, ContextTerm] = {}

    def add_recognition(text: str, weight: float, source: str, category: str) -> None:
        text = text.strip()
        if not text:
            return
        item = RecognitionHint(text, float(weight), source, category)
        current = recognition_by_text.get(text)
        if current is None or item.weight > current.weight:
            recognition_by_text[text] = item

    def add_correction(term: ContextTerm) -> None:
        text = term.text.strip()
        if not text:
            return
        current = correction_by_text.get(text)
        if current is None or term.weight > current.weight:
            correction_by_text[text] = term

    for learned in local:
        weight = _local_weight(learned.confirmations, policy)
        add_recognition(learned.confirmed, weight, "local-confirmed", learned.category)
        add_correction(ContextTerm(learned.confirmed, learned.category, weight, "local-confirmed"))

    for term in session_terms:
        add_recognition(term.text, term.weight, "session-context", term.category)
        add_correction(ContextTerm(term.text, term.category, term.weight, "session-context"))

    for term in core_terms:
        add_recognition(term.text, term.weight, term.source or "dore-core", term.category)
        add_correction(term)

    recognition = tuple(sorted(recognition_by_text.values(), key=lambda x: x.weight, reverse=True)[:policy.max_recognition_hints])
    correction = tuple(sorted(correction_by_text.values(), key=lambda x: x.weight, reverse=True)[:policy.max_correction_terms])
    return ResolvedContext(recognition=recognition, correction=correction)
