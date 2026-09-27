"""Deterministic pre-build regression gate for Chinese sermon subtitles.

The corpus grows from real failures, but the gate measures broad categories so
release quality cannot collapse into one-off typo patches.
"""
from __future__ import annotations
import json
from pathlib import Path

from church_language_context import vocabulary

ROOT = Path(__file__).resolve().parent


def main() -> None:
    data = json.loads((ROOT / "subtitle_regression_corpus.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    terms = set(vocabulary())
    categories = {case["category"] for case in cases}
    required = {"scripture", "names", "places", "theology", "church", "ordinary"}
    missing_categories = required - categories
    if missing_categories:
        raise AssertionError("Regression corpus missing categories: " + ", ".join(sorted(missing_categories)))

    domain_tokens = set()
    ordinary_cases = 0
    for case in cases:
        if case.get("must_not_change"):
            ordinary_cases += 1
            if case["must_keep"] != [case["input"]]:
                raise AssertionError("Ordinary-language preservation case is malformed")
        else:
            domain_tokens.update(case.get("must_keep", []))

    uncovered = sorted(token for token in domain_tokens if token not in terms)
    if uncovered:
        raise AssertionError("Domain regression tokens absent from local context: " + ", ".join(uncovered))
    if ordinary_cases < 2:
        raise AssertionError("Need ordinary-Chinese negative controls to detect overcorrection")

    print(
        "subtitle regression corpus: PASS "
        f"({len(cases)} cases, {len(domain_tokens)} domain probes, {ordinary_cases} negative controls)"
    )


if __name__ == "__main__":
    main()
