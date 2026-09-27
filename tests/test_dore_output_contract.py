"""Offline output-contract gate for Doré subtitle corrections.

The live endpoint cannot be a build dependency. This gate verifies the client
applies only explicit changed results, preserves SRT structure/timestamps, and
leaves ordinary Chinese untouched when the proofreader says no change.
"""
from unittest.mock import patch

from dore_proofreader import apply_dore_to_srt_text

SRT = """1
00:00:01,000 --> 00:00:04,000
我們今天讀以弗所書，談神的呼召。

2
00:00:05,000 --> 00:00:08,000
這一句只是普通中文，不需要潤色。

3
00:00:09,000 --> 00:00:12,000
保羅在這裡談到教會和恩典。
"""


def fake_response(segments, endpoint=None, timeout=30):
    rows = []
    for segment in segments:
        text = segment["text"]
        # Simulate one high-confidence domain correction without encoding a
        # production replacement rule in the app itself.
        if "呼召" in text:
            corrected = text.replace("呼召", "蒙召")
            rows.append({"id": segment["id"], "changed": True, "corrected": corrected})
        else:
            rows.append({"id": segment["id"], "changed": False, "corrected": "不應被採用的改寫"})
    return {
        "ok": True,
        "schema": "dore.subtitle-proofread.v1",
        "results": rows,
        "summary": {"segments": len(rows), "changed": 1},
    }


def main():
    with patch("dore_proofreader.proofread_segments", fake_response):
        corrected, summary = apply_dore_to_srt_text(SRT)

    assert "00:00:01,000 --> 00:00:04,000" in corrected
    assert "00:00:05,000 --> 00:00:08,000" in corrected
    assert "00:00:09,000 --> 00:00:12,000" in corrected
    assert "我們今天讀以弗所書，談神的蒙召。" in corrected
    assert "這一句只是普通中文，不需要潤色。" in corrected
    assert "保羅在這裡談到教會和恩典。" in corrected
    assert "不應被採用的改寫" not in corrected
    assert summary["changed"] == 1
    assert corrected.count("-->") == SRT.count("-->")
    print("dore output contract gate: PASS")


if __name__ == "__main__":
    main()
