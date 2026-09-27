#!/usr/bin/env python3
"""Run the fixed four-sermon URL corpus through the transcript-only ASR gate.

No video rendering is performed. Each URL is ingested as audio only and the
resulting transcript/gate report is retained under benchmark-results/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URLS = ROOT / "benchmarks" / "sermon_urls.txt"
OUT = ROOT / "benchmark-results"
RUNNER = ROOT / "tools" / "benchmark_url_asr.py"


def main() -> int:
    urls = [line.strip() for line in URLS.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    if not urls:
        raise SystemExit("benchmark corpus is empty")
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    failures = 0
    for index, url in enumerate(urls, 1):
        case_dir = OUT / f"sermon-{index:02d}"
        case_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(urls)}] {url}", flush=True)
        proc = subprocess.run([sys.executable, str(RUNNER), url, "--output", str(case_dir)], text=True)
        passed = proc.returncode == 0
        summary.append({"index": index, "url": url, "passed": passed, "result_dir": str(case_dir.relative_to(ROOT))})
        failures += 0 if passed else 1
    report = {"total": len(urls), "passed": len(urls) - failures, "failed": failures, "cases": summary}
    (OUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
