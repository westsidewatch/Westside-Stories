"""Local-first learning memory for Doré Subtitle Pack v2.

User-confirmed knowledge grows on-device. It is not a cloud dependency and is
scoped so one organisation/speaker/series does not contaminate another.
Automatic suggestions never become memory without explicit confirmation.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

MEMORY_SCHEMA = "dore.subtitle-local-memory.v1"


@dataclass(frozen=True)
class MemoryScope:
    organisation: str = ""
    speaker: str = ""
    series: str = ""


@dataclass(frozen=True)
class LearnedTerm:
    observed: str
    confirmed: str
    category: str
    scope: MemoryScope
    confirmations: int = 1
    last_confirmed_at: str = ""
    source: str = "user-confirmed"

    def key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.scope.organisation,
            self.scope.speaker,
            self.scope.series,
            self.observed,
            self.confirmed,
            self.category,
        )


def load_memory(path: Path) -> list[LearnedTerm]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != MEMORY_SCHEMA:
        raise ValueError("Unsupported local subtitle memory schema")
    result: list[LearnedTerm] = []
    for item in payload.get("terms") or []:
        scope = item.get("scope") or {}
        result.append(LearnedTerm(
            observed=str(item.get("observed") or ""),
            confirmed=str(item.get("confirmed") or ""),
            category=str(item.get("category") or "unknown"),
            scope=MemoryScope(
                organisation=str(scope.get("organisation") or ""),
                speaker=str(scope.get("speaker") or ""),
                series=str(scope.get("series") or ""),
            ),
            confirmations=max(1, int(item.get("confirmations", 1))),
            last_confirmed_at=str(item.get("last_confirmed_at") or ""),
            source="user-confirmed",
        ))
    return result


def save_memory(path: Path, terms: Iterable[LearnedTerm]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": MEMORY_SCHEMA,
        "local_only": True,
        "cloud_required": False,
        "terms": [asdict(term) for term in terms],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def confirm(
    terms: Iterable[LearnedTerm],
    *,
    observed: str,
    confirmed: str,
    category: str,
    scope: MemoryScope,
) -> list[LearnedTerm]:
    """Grow memory only from an explicit user-confirmed correction."""
    observed = observed.strip()
    confirmed = confirmed.strip()
    if not observed or not confirmed or observed == confirmed:
        return list(terms)

    now = datetime.now(timezone.utc).isoformat()
    incoming = LearnedTerm(observed, confirmed, category, scope)
    result: list[LearnedTerm] = []
    found = False
    for term in terms:
        if term.key() == incoming.key():
            result.append(LearnedTerm(
                observed=term.observed,
                confirmed=term.confirmed,
                category=term.category,
                scope=term.scope,
                confirmations=term.confirmations + 1,
                last_confirmed_at=now,
            ))
            found = True
        else:
            result.append(term)
    if not found:
        result.append(LearnedTerm(
            observed=observed,
            confirmed=confirmed,
            category=category,
            scope=scope,
            confirmations=1,
            last_confirmed_at=now,
        ))
    return result


def applicable_terms(terms: Iterable[LearnedTerm], scope: MemoryScope) -> list[LearnedTerm]:
    """Return only knowledge applicable to the current nested scope.

    Organisation-wide terms apply within that organisation; speaker terms only
    to that speaker; series terms only to that series. Empty stored fields are
    broader scopes, never wildcards across organisations.
    """
    result: list[LearnedTerm] = []
    for term in terms:
        saved = term.scope
        if saved.organisation and saved.organisation != scope.organisation:
            continue
        if saved.speaker and saved.speaker != scope.speaker:
            continue
        if saved.series and saved.series != scope.series:
            continue
        result.append(term)
    return result
