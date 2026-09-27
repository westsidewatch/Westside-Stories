"""Objective A/B gate for subtitle ASR engines.

A challenger may not enter production merely because it runs. It must beat the
baseline on verified transcript evidence without increasing ordinary-text
errors. Metrics are character error rate plus exact recall of annotated domain
terms. No correction dictionary participates in scoring.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


def _distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (ca != cb),
            ))
        previous = current
    return previous[-1]


def _normalise(text: str) -> str:
    return "".join(ch for ch in text.strip() if not ch.isspace())


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    reference: str
    baseline: str
    challenger: str
    domain_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class EngineScore:
    cer: float
    domain_recall: float
    characters: int
    domain_terms: int


@dataclass(frozen=True)
class BenchmarkDecision:
    baseline: EngineScore
    challenger: EngineScore
    promoted: bool
    reason: str


def _score(cases: Iterable[BenchmarkCase], field: str) -> EngineScore:
    edits = chars = hits = terms = 0
    for case in cases:
        ref = _normalise(case.reference)
        hyp = _normalise(getattr(case, field))
        edits += _distance(ref, hyp)
        chars += max(1, len(ref))
        for term in case.domain_terms:
            terms += 1
            if term and term in hyp:
                hits += 1
    return EngineScore(
        cer=edits / chars if chars else 0.0,
        domain_recall=hits / terms if terms else 1.0,
        characters=chars,
        domain_terms=terms,
    )


def decide(cases: Iterable[BenchmarkCase], minimum_relative_cer_gain: float = 0.05) -> BenchmarkDecision:
    material = tuple(cases)
    if not material:
        raise ValueError("ASR benchmark requires verified cases")
    baseline = _score(material, "baseline")
    challenger = _score(material, "challenger")
    if baseline.cer == 0:
        promoted = challenger.cer == 0 and challenger.domain_recall >= baseline.domain_recall
        gain = 0.0
    else:
        gain = (baseline.cer - challenger.cer) / baseline.cer
        promoted = (
            challenger.cer < baseline.cer
            and gain >= minimum_relative_cer_gain
            and challenger.domain_recall >= baseline.domain_recall
        )
    reason = (
        f"baseline CER={baseline.cer:.4f}, challenger CER={challenger.cer:.4f}, "
        f"relative gain={gain:.1%}; baseline domain recall={baseline.domain_recall:.1%}, "
        f"challenger domain recall={challenger.domain_recall:.1%}"
    )
    return BenchmarkDecision(baseline, challenger, promoted, reason)
