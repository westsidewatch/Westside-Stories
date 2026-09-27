"""Fast, local Chinese church/Bible subtitle correction.

Runs after ASR and before SRT render. It never touches timestamps and does not
require Doré, a network service, or another ASR pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

try:
    from pypinyin import Style, lazy_pinyin
except Exception:  # explicit mappings still work without optional fuzzy deps
    Style = lazy_pinyin = None
try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None

DEFAULT_TERMS = Path(__file__).with_name("context") / "church-bible-zh.txt"
DEFAULT_EXPLICIT = {
    "木道": "慕道",
    "恩昭": "恩召",
}

@dataclass(frozen=True)
class Correction:
    original: str
    replacement: str
    score: float


def _pinyin(text: str) -> str:
    if lazy_pinyin is None or Style is None:
        return ""
    return "".join(lazy_pinyin(text, style=Style.NORMAL, errors="ignore")).lower()


def load_terms(path: Path = DEFAULT_TERMS) -> list[str]:
    if not path.exists():
        return []
    out, seen = [], set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        term = raw.strip()
        if not term or term.startswith("#") or term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def correct_text(text: str, *, terms: Iterable[str] | None = None,
                 explicit: dict[str, str] | None = None,
                 threshold: float = 0.94) -> tuple[str, list[Correction]]:
    """Correct known errors first, then conservative same-length pinyin matches."""
    updated = text
    changes: list[Correction] = []
    mapping = dict(DEFAULT_EXPLICIT)
    if explicit:
        mapping.update(explicit)
    for wrong, right in sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True):
        if wrong in updated:
            count = updated.count(wrong)
            updated = updated.replace(wrong, right)
            changes.extend(Correction(wrong, right, 1.0) for _ in range(count))

    if fuzz is None or lazy_pinyin is None:
        return updated, changes

    targets = list(terms) if terms is not None else load_terms()
    buckets: dict[int, list[tuple[str, str]]] = {}
    for target in targets:
        if len(target) < 2:
            continue
        buckets.setdefault(len(target), []).append((target, _pinyin(target)))

    # Conservative: Chinese-only windows, same character length, very high score.
    for length, candidates in buckets.items():
        pattern = re.compile(rf"[\u3400-\u9fff]{{{length}}}")
        pos = 0
        while pos <= len(updated) - length:
            segment = updated[pos:pos + length]
            if not pattern.fullmatch(segment):
                pos += 1
                continue
            seg_py = _pinyin(segment)
            best = None
            for target, target_py in candidates:
                if segment == target or not seg_py or not target_py:
                    continue
                score = fuzz.ratio(seg_py, target_py) / 100.0
                if score >= threshold and (best is None or score > best[0]):
                    best = (score, target)
            if best:
                score, target = best
                updated = updated[:pos] + target + updated[pos + length:]
                changes.append(Correction(segment, target, round(score, 4)))
                pos += length
            else:
                pos += 1
    return updated, changes


def apply_to_srt_text(srt_text: str, **kwargs) -> tuple[str, dict]:
    """Correct only subtitle text lines; preserve indices/timestamps verbatim."""
    lines = srt_text.splitlines()
    changed = 0
    matches = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.isdigit() or "-->" in line:
            continue
        corrected, edits = correct_text(line, **kwargs)
        if edits:
            lines[i] = corrected
            changed += 1
            matches += len(edits)
    suffix = "\n" if srt_text.endswith("\n") else ""
    return "\n".join(lines) + suffix, {"changed_lines": changed, "corrections": matches}
