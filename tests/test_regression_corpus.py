"""Deterministic regression-data integrity gate for Chinese sermon subtitles.

Observed ASR failures remain evidence only. Product code must not contain a
source->target replacement table; phonetic/contextual behavior is tested by the
specialized gates.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    data = json.loads((ROOT / "subtitle_regression_corpus.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    categories = {case["category"] for case in cases}
    required = {"scripture", "names", "places", "theology", "church", "ordinary"}
    missing = required - categories
    if missing:
        raise AssertionError("Regression corpus missing categories: " + ", ".join(sorted(missing)))

    ordinary = [case for case in cases if case.get("must_not_change")]
    observed = [case for case in cases if case.get("expected_local")]
    if len(ordinary) < 2:
        raise AssertionError("Need ordinary-Chinese negative controls")
    if len(observed) < 2:
        raise AssertionError("Need observed ASR failures as evidence")
    for case in observed:
        if case["input"] == case["expected_local"]:
            raise AssertionError("Observed failure must differ from verified reference")

    print(f"subtitle regression evidence: PASS ({len(cases)} cases, {len(observed)} observed failures, {len(ordinary)} negative controls)")


if __name__ == "__main__":
    main()
