"""Expandable corpus loader for contextual Chinese ASR.

The production recognizer consumes corpus evidence, not transcript substitutions.
Additional corpora can be dropped into APP_HOME/context/*.txt without code changes.
Each non-empty line is one contextual term or phrase; # starts a comment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _read_terms(path: Path) -> list[str]:
    if not path.is_file():
        return []
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if text and not text.startswith("#"):
            out.append(text)
    return out


def load_context_terms(app_home: Path, extra_paths: Iterable[Path] = ()) -> list[str]:
    """Load all available Bible/church/current-job context without a code-level word list."""
    roots = [Path(__file__).resolve().parents[1] / "context", app_home / "context"]
    paths: list[Path] = []
    for root in roots:
        if root.is_dir():
            paths.extend(sorted(root.glob("*.txt")))
    paths.extend(extra_paths)

    seen: set[str] = set()
    terms: list[str] = []
    for path in paths:
        for term in _read_terms(path):
            if term not in seen:
                seen.add(term)
                terms.append(term)
    return terms
