"""Westside Stories 1.1 production entrypoint.

Keeps the stable main.py subtitle path intact while attaching Doré v2 as a
fail-open, post-ASR shadow observer. Doré cannot block or mutate SRT output.
"""
from __future__ import annotations

from main import APP_HOME, Worker, log, main

_original_write_srt = Worker.write_srt


def _write_srt_with_shadow(self, result_json, srt_path):
    # Stable authority first: produce the same SRT as 1.0.
    _original_write_srt(self, result_json, srt_path)

    # Optional local observer second. Import/runtime failure is deliberately
    # isolated so Doré can never turn a successful transcription into failure.
    try:
        from dore_subtitle.pipeline_bridge import run_shadow_pipeline
        report = run_shadow_pipeline(result_json, APP_HOME)
        if report.get("ok"):
            log(
                "dore shadow: ok; "
                f"segments={report.get('segments', 0)}; "
                f"suspicions={report.get('suspicions', 0)}"
            )
        else:
            log("dore shadow: skipped; " + str(report.get("error", "unknown")))
    except Exception as exc:
        log(f"dore shadow: isolated failure: {type(exc).__name__}: {exc}")


Worker.write_srt = _write_srt_with_shadow


if __name__ == "__main__":
    main()
