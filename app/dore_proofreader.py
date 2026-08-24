"""Doré subtitle proofreader client for Westside Stories.

Conservative by design: Doré may normalize high-confidence biblical terminology,
but it never rewrites uncertain subtitle language.
"""
from __future__ import annotations
import json
import os
import urllib.request
from typing import Iterable

DEFAULT_ENDPOINT = "https://westsidewatch.ca/api/dore/subtitle-proofread"


def proofread_segments(segments: Iterable[dict], endpoint: str | None = None, timeout: int = 30) -> dict:
    url = endpoint or os.environ.get("DORE_PROOFREADER_URL", DEFAULT_ENDPOINT)
    payload = json.dumps({"segments": list(segments)}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Westside-Stories/Dore-Worker"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not data.get("ok") or data.get("schema") != "dore.subtitle-proofread.v1":
        raise RuntimeError(f"Unexpected Doré response: {data}")
    return data


def apply_dore_to_srt_text(srt_text: str, endpoint: str | None = None) -> tuple[str, dict]:
    """Proofread subtitle payload while preserving SRT indices/timestamps exactly."""
    lines = srt_text.splitlines()
    candidates = []
    line_ids = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.isdigit() or "-->" in line:
            continue
        line_ids.append(i)
        candidates.append({"id": i, "text": line})
    if not candidates:
        return srt_text, {"segments": 0, "changed": 0}
    result = proofread_segments(candidates, endpoint=endpoint)
    by_id = {int(item["id"]): item for item in result["results"]}
    for i in line_ids:
        item = by_id.get(i)
        if item and item.get("changed"):
            lines[i] = item["corrected"]
    suffix = "\n" if srt_text.endswith("\n") else ""
    return "\n".join(lines) + suffix, result.get("summary", {})
