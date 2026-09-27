#!/usr/bin/env python3
"""Create Doré v2 evidence from an existing Whisper JSON without touching SRT."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from dore_subtitle.shadow_archive import write_shadow_archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("whisper_json", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    source = args.whisper_json
    destination = args.out or source.with_name(source.stem + ".dore-shadow.json")
    result = json.loads(source.read_text(encoding="utf-8"))
    write_shadow_archive(result, destination)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
