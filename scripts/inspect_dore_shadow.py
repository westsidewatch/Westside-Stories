#!/usr/bin/env python3
"""Inspect a Doré shadow archive without modifying subtitles."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dore_subtitle.evidence_packet import EvidencePacket, WordEvidence
from dore_subtitle.suspicion_gate import inspect_all


def packet_from_dict(item: dict) -> EvidencePacket:
    return EvidencePacket(
        segment_id=str(item.get("segment_id", "")),
        original_text=str(item.get("original_text", "")),
        start=float(item.get("start", 0) or 0),
        end=float(item.get("end", 0) or 0),
        avg_logprob=item.get("avg_logprob"),
        no_speech_prob=item.get("no_speech_prob"),
        compression_ratio=item.get("compression_ratio"),
        words=tuple(WordEvidence(**word) for word in (item.get("words") or [])),
        previous_text=str(item.get("previous_text", "")),
        next_text=str(item.get("next_text", "")),
        context_tags=tuple(item.get("context_tags") or ()),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("shadow_json", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.shadow_json.read_text(encoding="utf-8"))
    packets = [packet_from_dict(item) for item in payload.get("segments", [])]
    suspicions = inspect_all(packets)
    print(json.dumps([
        {
            "segment_id": item.segment_id,
            "reasons": item.reasons,
            "word_indexes": item.word_indexes,
        }
        for item in suspicions
    ], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
