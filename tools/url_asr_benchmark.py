#!/usr/bin/env python3
"""URL -> audio-only -> contextual Chinese ASR -> transcript benchmark.

This deliberately stops before subtitle burn-in. It is the release gate for ASR
quality so users never need to render a full video to test recognition changes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from asr.church_context import load_context_terms
from dore_subtitle.context_retriever import CorpusTerm, retrieve_context
from dore_subtitle.contextual_paraformer import transcribe_challenger
from dore_subtitle.local_memory import MemoryScope
from media_url import download_audio, is_media_url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--python", default=sys.executable, help="Python executable containing FunASR")
    parser.add_argument("--expect", action="append", default=[], help="Required term; repeatable")
    parser.add_argument("--query", default="中文教會 聖經 講道 慕道 恩召 錫安")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not is_media_url(args.url):
        raise SystemExit("invalid media URL")

    scope = MemoryScope(
        organisation=os.environ.get("WESTSIDE_ORGANISATION", "Living Water West"),
        speaker=os.environ.get("WESTSIDE_SPEAKER", ""),
        series=os.environ.get("WESTSIDE_SERIES", ""),
    )
    corpus = [CorpusTerm(text=t, evidence="production church/Bible corpus", weight=2.0)
              for t in load_context_terms(ROOT / "app")]
    context = retrieve_context(scope=scope, corpus_terms=corpus, query=args.query, limit=128)

    with tempfile.TemporaryDirectory(prefix="westside-url-asr-") as tmp:
        audio = download_audio(args.url, Path(tmp))
        result = transcribe_challenger(args.python, audio, context=context)

    if not result.ok:
        raise SystemExit("ASR failed: " + (result.error or "unknown error"))

    text = result.text.strip()
    missing = [term for term in args.expect if term not in text]
    payload = {
        "backend": result.backend,
        "context_terms": len(context),
        "characters": len(text),
        "expected": args.expect,
        "missing": missing,
        "pass": not missing,
        "text": text,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text)
        print("\nGATE:", "PASS" if not missing else "FAIL")
        if missing:
            print("Missing:", "、".join(missing))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
