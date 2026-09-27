"""Deterministic pre-build regression gate for Chinese sermon subtitles."""
from __future__ import annotations
import json
from pathlib import Path

from church_language_context import vocabulary
from dore_subtitle.domain_recovery import recover_domain_text

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
    recovery_cases = 0
    for case in cases:
        recovered, _ = recover_domain_text(case["input"])
        if case.get("must_not_change"):
            ordinary_cases += 1
            if recovered != case["input"]:
                raise AssertionError(f"Ordinary Chinese overcorrected: {case['input']} -> {recovered}")
        else:
            domain_tokens.update(case.get("must_keep", []))
        if "expected_local" in case:
            recovery_cases += 1
            if recovered != case["expected_local"]:
                raise AssertionError(f"Local recovery failed: {case['input']} -> {recovered}; expected {case['expected_local']}")

    uncovered = sorted(token for token in domain_tokens if token not in terms)
    if uncovered:
        raise AssertionError("Domain regression tokens absent from local context: " + ", ".join(uncovered))
    if ordinary_cases < 2:
        raise AssertionError("Need ordinary-Chinese negative controls to detect overcorrection")
    if recovery_cases < 2:
        raise AssertionError("Need observed ASR recovery cases in release gate")

    print(f"subtitle regression corpus: PASS ({len(cases)} cases, {recovery_cases} real recovery cases, {ordinary_cases} negative controls)")


if __name__ == "__main__":
    main()
