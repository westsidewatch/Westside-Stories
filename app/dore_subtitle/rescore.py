"""Conservative rescoring for Doré subtitle candidates.

Scores are diagnostic only. They never authorize transcript mutation. The
policy intentionally requires multiple independent signals before a candidate
can even be marked review-worthy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .context_candidates import Candidate
from .suspicion_gate import Suspicion


@dataclass(frozen=True)
class RescorePolicy:
    minimum_similarity: float = 0.68
    minimum_context_weight: float = 1.0
    review_threshold: float = 0.72
    high_threshold: float = 0.86


@dataclass(frozen=True)
class RescoredCandidate:
    candidate: Candidate
    score: float
    decision: str
    authority: str = "review-only"
    mutates_subtitles: bool = False

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["candidate"] = asdict(self.candidate)
        return payload


def rescore(candidate: Candidate, suspicion: Suspicion, policy: RescorePolicy | None = None) -> RescoredCandidate:
    policy = policy or RescorePolicy()

    # Lexical evidence remains primary; local/context weight may strengthen but
    # never replace it. Suspicion is required as an independent upstream gate.
    similarity = max(0.0, min(1.0, candidate.lexical_similarity))
    context = max(0.0, min(1.0, candidate.context_weight / 2.5))
    suspicious = 1.0 if suspicion.suspicious else 0.0
    score = round((similarity * 0.62) + (context * 0.23) + (suspicious * 0.15), 4)

    if not suspicion.suspicious:
        decision = "reject-no-suspicion"
    elif similarity < policy.minimum_similarity:
        decision = "reject-low-similarity"
    elif candidate.context_weight < policy.minimum_context_weight:
        decision = "reject-weak-context"
    elif score >= policy.high_threshold:
        decision = "review-high"
    elif score >= policy.review_threshold:
        decision = "review"
    else:
        decision = "reject-below-threshold"

    return RescoredCandidate(candidate=candidate, score=score, decision=decision)
