"""Fail-open bridge from the stable subtitle pipeline into Doré v2.

This bridge deliberately has no correction authority. It consumes an existing
Whisper result after transcription, writes local shadow evidence, and reports
suspicion metadata. Any failure is returned as diagnostics and must never block
SRT generation or video burn-in.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .shadow_archive import packets_from_whisper, write_shadow_archive
from .suspicion_gate import inspect_all


def run_shadow_pipeline(result_json: Path, app_home: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": "SHADOW",
        "mutates_subtitles": False,
        "ok": False,
        "segments": 0,
        "suspicions": 0,
    }
    try:
        result = json.loads(result_json.read_text(encoding="utf-8"))
        packets = packets_from_whisper(result)
        shadow_path = app_home / "dore" / "last_result.dore-shadow.json"
        suspicion_path = app_home / "dore" / "last_result.dore-suspicions.json"

        write_shadow_archive(result, shadow_path)
        suspicions = inspect_all(packets)
        suspicion_path.parent.mkdir(parents=True, exist_ok=True)
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

        report.update(
            ok=True,
            segments=len(packets),
            suspicions=len(suspicions),
            shadow_path=str(shadow_path),
            suspicion_path=str(suspicion_path),
        )
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
    return report
