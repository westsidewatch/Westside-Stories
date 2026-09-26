"""Build a local shadow archive from an untouched Whisper result.

This module never edits transcript text or timestamps and never calls a remote
service. Failure to archive evidence must never block subtitle production.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_packet import EvidencePacket, WordEvidence, SCHEMA


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def packets_from_whisper(result: dict[str, Any]) -> list[EvidencePacket]:
    segments = result.get("segments") or []
    packets: list[EvidencePacket] = []
    for index, segment in enumerate(segments):
        original = str(segment.get("text") or "")
        words = tuple(
            WordEvidence(
                text=str(word.get("word") or word.get("text") or ""),
                start=_number(word.get("start")),
                end=_number(word.get("end")),
                probability=_number(word.get("probability")),
            )
            for word in (segment.get("words") or [])
        )
        previous_text = str(segments[index - 1].get("text") or "") if index else ""
        next_text = str(segments[index + 1].get("text") or "") if index + 1 < len(segments) else ""
        packets.append(EvidencePacket(
            segment_id=str(segment.get("id", index)),
            original_text=original,
            start=float(segment.get("start", 0) or 0),
            end=float(segment.get("end", segment.get("start", 0)) or 0),
            avg_logprob=_number(segment.get("avg_logprob")),
            no_speech_prob=_number(segment.get("no_speech_prob")),
            compression_ratio=_number(segment.get("compression_ratio")),
            words=words,
            previous_text=previous_text,
            next_text=next_text,
        ))
    return packets


def write_shadow_archive(result: dict[str, Any], destination: Path) -> Path:
    packets = packets_from_whisper(result)
    payload = {
        "schema": SCHEMA,
        "mode": "SHADOW",
        "authority": "whisper-original",
        "mutates_subtitles": False,
        "segments": [packet.to_dict() for packet in packets],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
