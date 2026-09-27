"""Chinese church-language context contract.

Static hand-maintained church/Bible vocabulary was removed. Domain recovery must
be driven by real evidence, phonetic/contextual candidates and learned local
memory rather than a fixed 182-term allow-list.
"""
from __future__ import annotations


def vocabulary() -> list[str]:
    """Compatibility shim: the former static vocabulary has been retired."""
    return []


def context_payload() -> dict:
    return {
        "schema": "westside.church-language-context.v3",
        "language": "zh-Hant",
        "domain": "Chinese Christian sermon and Bible teaching",
        "preserve_spoken_wording": True,
        "terms": [],
        "static_vocabulary": False,
    }
