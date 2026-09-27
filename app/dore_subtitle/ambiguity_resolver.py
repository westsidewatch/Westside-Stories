"""Build ambiguity evidence for Doré without performing blind replacements.

Only phonetic candidates backed by the current Dynamic Context are exposed.
Doré remains the semantic decision layer; weak evidence never authorizes a
local transcript mutation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .dynamic_context import DynamicTerm
from .phonetic_rescorer import candidates_for_span


@dataclass(frozen=True)
class AmbiguityEvidence:
    observed: str
    candidates: tuple[dict, ...]


def build_ambiguity_evidence(
    observed_spans: Iterable[str],
    context: Iterable[DynamicTerm],
    *,
    minimum_phonetic_similarity: float = 0.72,
    candidate_limit: int = 4,
) -> list[AmbiguityEvidence]:
    pack = tuple(context)
    evidence: list[AmbiguityEvidence] = []
    seen: set[str] = set()
    for raw in observed_spans:
        observed = (raw or "").strip()
        if len(observed) < 2 or observed in seen:
            continue
        seen.add(observed)
        ranked = candidates_for_span(
            observed,
            pack,
            minimum_phonetic_similarity=minimum_phonetic_similarity,
            limit=candidate_limit,
        )
        if not ranked:
            continue
        evidence.append(AmbiguityEvidence(
            observed=observed,
            candidates=tuple(asdict(item) for item in ranked),
        ))
    return evidence


def as_payload(evidence: Iterable[AmbiguityEvidence]) -> list[dict]:
    return [
        {"observed": item.observed, "candidates": list(item.candidates)}
        for item in evidence
    ]
