"""Doré subtitle proofreader client for Westside Stories.

The proofreader receives Chinese church/Bible domain context plus optional
on-device learned context, and makes only high-confidence local corrections.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import urllib.request
from typing import Iterable

from church_language_context import context_payload
from dore_subtitle.local_context_adapter import build_local_context
from dore_subtitle.local_memory import MemoryScope

DEFAULT_ENDPOINT = "https://westsidewatch.ca/api/dore/subtitle-proofread"
DEFAULT_MEMORY = Path.home() / "Library" / "Application Support" / "Westside Stories" / "subtitle-memory.json"


def proofread_segments(segments: Iterable[dict], endpoint: str | None = None, timeout: int = 30, scope: MemoryScope | None = None) -> dict:
    url = endpoint or os.environ.get("DORE_PROOFREADER_URL", DEFAULT_ENDPOINT)
    active_scope = scope or MemoryScope()
    local_context = build_local_context(DEFAULT_MEMORY, active_scope)
    payload = json.dumps(
        {
            "segments": list(segments),
            "context": context_payload(),
            "local_context": local_context,
            "policy": {
                "apply_high_confidence": True,
                "minimal_local_edits_only": True,
                "preserve_timestamps": True,
                "preserve_spoken_wording": True,
                "no_style_rewrite": True,
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Westside-Stories/Dore-Worker"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not data.get("ok") or data.get("schema") != "dore.subtitle-proofread.v1":
        raise RuntimeError(f"Unexpected Doré response: {data}")
    return data


def apply_dore_to_srt_text(srt_text: str, endpoint: str | None = None, scope: MemoryScope | None = None) -> tuple[str, dict]:
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
    result = proofread_segments(candidates, endpoint=endpoint, scope=scope)
    by_id = {int(item["id"]): item for item in result["results"]}
    for i in line_ids:
        item = by_id.get(i)
        if item and item.get("changed") and item.get("corrected"):
            lines[i] = item["corrected"]
    suffix = "\n" if srt_text.endswith("\n") else ""
    return "\n".join(lines) + suffix, result.get("summary", {})
