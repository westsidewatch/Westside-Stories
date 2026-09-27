"""Read scoped subtitle knowledge from the existing on-device memory."""
from __future__ import annotations

from pathlib import Path

from .local_memory import MemoryScope, applicable_terms, load_memory


def build_local_context(path: Path, scope: MemoryScope) -> dict:
    try:
        learned = applicable_terms(load_memory(path), scope)
    except (OSError, ValueError):
        learned = []

    return {
        "schema": "dore.subtitle-local-context.v1",
        "scope": {
            "organisation": scope.organisation,
            "speaker": scope.speaker,
            "series": scope.series,
        },
        "terms": [
            {
                "observed": term.observed,
                "confirmed": term.confirmed,
                "category": term.category,
                "confirmations": term.confirmations,
            }
            for term in learned
        ],
    }
