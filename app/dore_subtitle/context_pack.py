"""Versioned local context packs for subtitle candidate generation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .context_candidates import ContextTerm

PACK_SCHEMA = "dore.subtitle-context-pack.v1"


@dataclass(frozen=True)
class ContextPack:
    version: str
    terms: tuple[ContextTerm, ...]
    schema: str = PACK_SCHEMA


def load_context_pack(path: Path) -> ContextPack:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != PACK_SCHEMA:
        raise ValueError("Unsupported Doré subtitle context pack schema")
    version = str(payload.get("version") or "").strip()
    if not version:
        raise ValueError("Doré subtitle context pack has no version")
    terms = tuple(
        ContextTerm(
            text=str(item.get("text") or "").strip(),
            category=str(item.get("category") or "unknown"),
            weight=float(item.get("weight", 1.0)),
            source=str(item.get("source") or "local-pack"),
        )
        for item in (payload.get("terms") or [])
        if str(item.get("text") or "").strip()
    )
    return ContextPack(version=version, terms=terms)
