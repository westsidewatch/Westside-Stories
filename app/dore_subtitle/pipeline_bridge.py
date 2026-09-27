"""Fail-open bridge from the stable subtitle pipeline into Doré v2.

This bridge deliberately has no correction authority. It consumes an existing
Whisper result after transcription, writes local shadow evidence, and reports
suspicion/candidate metadata. Any failure is returned as diagnostics and must
never block SRT generation or video burn-in.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .context_candidates import ContextTerm, propose
from .local_memory import MemoryScope, applicable_terms, load_memory
from .rescore import rescore
from .shadow_archive import packets_from_whisper, write_shadow_archive
from .suspicion_gate import inspect_all


def _local_terms(app_home: Path, scope: MemoryScope) -> list[ContextTerm]:
    memory_path = app_home / "dore" / "local-memory.json"
    learned = applicable_terms(load_memory(memory_path), scope)
    return [
        ContextTerm(
            text=item.confirmed,
            category=item.category,
            weight=min(2.5, 1.0 + max(0, item.confirmations - 1) * 0.15),
            source="local-confirmed",
        )
        for item in learned
    ]


def run_shadow_pipeline(
    result_json: Path,
    app_home: Path,
    *,
    scope: MemoryScope | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": "SHADOW",
        "mutates_subtitles": False,
        "ok": False,
        "segments": 0,
        "suspicions": 0,
        "candidates": 0,
        "reviewable": 0,
    }
    try:
        result = json.loads(result_json.read_text(encoding="utf-8"))
        packets = packets_from_whisper(result)
        shadow_dir = app_home / "dore"
        shadow_path = shadow_dir / "last_result.dore-shadow.json"
        suspicion_path = shadow_dir / "last_result.dore-suspicions.json"
        candidate_path = shadow_dir / "last_result.dore-candidates.json"

        write_shadow_archive(result, shadow_path)
        suspicions = inspect_all(packets)
        suspicion_by_id = {item.segment_id: item for item in suspicions}
        terms = _local_terms(app_home, scope or MemoryScope())

        rescored = []
        for packet in packets:
            suspicion = suspicion_by_id.get(packet.segment_id)
            if suspicion is None or not suspicion.suspicious:
                continue
            for candidate in propose(packet, suspicion, terms):
                rescored.append(rescore(candidate, suspicion))

        shadow_dir.mkdir(parents=True, exist_ok=True)
        suspicion_path.write_text(
            json.dumps(
                {
                    "mode": "SHADOW",
                    "mutates_subtitles": False,
                    "items": [asdict(item) for item in suspicions],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        candidate_path.write_text(
            json.dumps(
                {
                    "mode": "SHADOW",
                    "authority": "review-only",
                    "mutates_subtitles": False,
                    "scope": asdict(scope or MemoryScope()),
                    "items": [item.to_dict() for item in rescored],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        report.update(
            ok=True,
            segments=len(packets),
            suspicions=len(suspicions),
            candidates=len(rescored),
            reviewable=sum(1 for item in rescored if item.decision.startswith("review")),
            shadow_path=str(shadow_path),
            suspicion_path=str(suspicion_path),
            candidate_path=str(candidate_path),
        )
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    return report
