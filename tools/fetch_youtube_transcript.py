#!/usr/bin/env python3
"""Caption-first benchmark ingestion.

Fetches timed YouTube captions without downloading video/audio. This is the
first-stage locator for known ASR errors; audio ASR remains a separate gate.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi


def video_id(value: str) -> str:
    p = urlparse(value)
    if p.netloc in {"youtu.be", "www.youtu.be"}:
        return p.path.strip("/").split("/")[0]
    if "youtube.com" in p.netloc:
        return parse_qs(p.query).get("v", [""])[0]
    return value.strip()


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://youtu.be/Z0L3jXp7h-U"
    vid = video_id(url)
    if not vid:
        raise SystemExit("invalid YouTube URL")
    out = Path(".benchmark-real") / vid
    out.mkdir(parents=True, exist_ok=True)

    api = YouTubeTranscriptApi()
    transcript_list = api.list(vid)
    preferred = None
    for lang in ("zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "zh", "en"):
        try:
            preferred = transcript_list.find_transcript([lang])
            break
        except Exception:
            pass
    if preferred is None:
        preferred = next(iter(transcript_list))

    rows = preferred.fetch().to_raw_data()
    text = "\n".join(str(x.get("text", "")) for x in rows)
    (out / "youtube-caption.txt").write_text(text, encoding="utf-8")
    (out / "youtube-caption.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    needles = ["木道", "慕道", "恩召", "西安", "錫安", "锡安"]
    hits = []
    for row in rows:
        t = str(row.get("text", ""))
        found = [n for n in needles if n in t]
        if found:
            hits.append({"start": row.get("start"), "duration": row.get("duration"), "text": t, "terms": found})
    (out / "known-error-locations.json").write_text(
        json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"video_id": vid, "caption_rows": len(rows), "known_error_hits": hits}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
