"""Full-transcript diagnostics for real sermon ASR benchmarks.

This module does not rewrite transcripts. It measures text-level signals so a
candidate engine cannot be accepted merely because three known words improved.
When verified reference text exists, the existing CER benchmark remains the
authoritative promotion gate; these diagnostics add corpus-wide visibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

_CJK = re.compile(r"[\u3400-\u9fff]")
_PUNCT = set("，。！？；：、,.!?;:\"'（）()【】[]《》<>—-…")


@dataclass(frozen=True)
class TranscriptDiagnostics:
    characters: int
    cjk_characters: int
    domain_hits: int
    domain_terms_present: tuple[str, ...]
    suspicious_latin_runs: int
    replacement_chars: int
    punctuation: int

    @property
    def cjk_ratio(self) -> float:
        return self.cjk_characters / self.characters if self.characters else 0.0


def diagnose(text: str, domain_terms: Iterable[str] = ()) -> TranscriptDiagnostics:
    clean = (text or "").strip()
    visible = [ch for ch in clean if not ch.isspace()]
    present = tuple(sorted({term for term in domain_terms if term and term in clean}))
    latin_runs = re.findall(r"[A-Za-z]{4,}", clean)
    return TranscriptDiagnostics(
        characters=len(visible),
        cjk_characters=sum(1 for ch in visible if _CJK.fullmatch(ch)),
        domain_hits=len(present),
        domain_terms_present=present,
        suspicious_latin_runs=len(latin_runs),
        replacement_chars=clean.count("�"),
        punctuation=sum(1 for ch in visible if ch in _PUNCT),
    )


def compare(baseline: str, challenger: str, domain_terms: Iterable[str] = ()) -> dict:
    """Return corpus-wide diagnostics without pretending to know ground truth."""
    b = diagnose(baseline, domain_terms)
    c = diagnose(challenger, domain_terms)
    return {
        "baseline": b,
        "challenger": c,
        "character_delta": c.characters - b.characters,
        "domain_hit_delta": c.domain_hits - b.domain_hits,
        "cjk_ratio_delta": c.cjk_ratio - b.cjk_ratio,
        "replacement_char_delta": c.replacement_chars - b.replacement_chars,
        "suspicious_latin_run_delta": c.suspicious_latin_runs - b.suspicious_latin_runs,
    }
