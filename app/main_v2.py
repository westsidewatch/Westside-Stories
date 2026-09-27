"""Westside Stories 1.1 production entrypoint.

Restores the proven v1 Doré proofreading path as the release baseline, while
keeping v1.1 shadow evidence, local learning infrastructure and adaptive burn-in
styles. Proofreading is fail-open: a network/Doré failure keeps the Whisper SRT
usable rather than failing the whole job.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import main as stable_main
from main import APP_HOME, Worker, log
from subtitle_style import profile_for_video

stable_main.APP_VERSION = "1.1"

_original_write_srt = Worker.write_srt


def _active_memory_scope():
    """Resolve optional local scope without making cloud/profile data mandatory.

    Existing installs continue to work with an empty scope. Deployments that
    know their local organisation/speaker/series can set these locally; the
    values are used only to select on-device learned terms.
    """
    from dore_subtitle.local_memory import MemoryScope
    return MemoryScope(
        organisation=os.environ.get("WESTSIDE_ORGANISATION", "").strip(),
        speaker=os.environ.get("WESTSIDE_SPEAKER", "").strip(),
        series=os.environ.get("WESTSIDE_SERIES", "").strip(),
    )


def _write_srt_with_proofreading_and_shadow(self, result_json, srt_path):
    # 1. Always produce the stable local Whisper SRT first.
    _original_write_srt(self, result_json, srt_path)

    # 2. Restore the v1 proofreading capability that users already relied on.
    #    Preserve the original SRT so every automatic correction is reversible.
    original_text = srt_path.read_text(encoding="utf-8")
    original_path = APP_HOME / "dore" / "last_result.whisper-original.srt"
    try:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.write_text(original_text, encoding="utf-8", newline="\n")
    except Exception as exc:
        log(f"original SRT archive skipped: {type(exc).__name__}: {exc}")

    try:
        from dore_proofreader import apply_dore_to_srt_text
        scope = _active_memory_scope()
        corrected, summary = apply_dore_to_srt_text(original_text, scope=scope)
        srt_path.write_text(corrected, encoding="utf-8", newline="\n")
        log(
            "Doré proofread restored: "
            f"segments={summary.get('segments', 0)} "
            f"changed={summary.get('changed', 0)}"
        )
    except Exception as exc:
        # Doré must improve the product, never become a runtime dependency.
        log(f"Doré proofread unavailable; kept Whisper SRT: {type(exc).__name__}: {exc}")

    # 3. v1.1 evidence remains observational and cannot undo the proven output.
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


def _probe_video_size(ffmpeg: str, video: Path) -> tuple[int | None, int | None]:
    ffprobe = str(Path(ffmpeg).with_name("ffprobe"))
    if not Path(ffprobe).is_file():
        return None, None
    try:
        p = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(video)],
            text=True, capture_output=True, env=stable_main.os.environ.copy(),
        )
        width, height = (p.stdout or "").strip().split("x", 1)
        return int(width), int(height)
    except Exception:
        return None, None


def _burn_with_style(self, ffmpeg: str, srt: Path, output: Path):
    self.status.emit("正在燒錄字幕到影片…", "Burning subtitles into video…")
    self.progress.emit(75)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        shutil.copyfile(srt, tmp_path)

        width, height = _probe_video_size(ffmpeg, self.video)
        style = profile_for_video(width, height)
        force_style = style.ass_force_style().replace("'", "\\'")
        subtitle_filter = (
            "subtitles=filename='" + str(tmp_path).replace("'", "\\'") +
            "':force_style='" + force_style + "'"
        )
        log(f"subtitle style: {width}x{height}; {style.ass_force_style()}")

        cmd = [
            ffmpeg, "-y", "-i", str(self.video),
            "-vf", subtitle_filter,
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "copy", str(output),
        ]
        p = subprocess.run(cmd, text=True, capture_output=True, env=stable_main.os.environ.copy())
        log("ffmpeg stdout:\n" + (p.stdout or ""))
        log("ffmpeg stderr:\n" + (p.stderr or ""))
        if p.returncode != 0:
            raise RuntimeError(
                "FFmpeg 燒錄失敗。\nFFmpeg burn-in failed.\n\n"
                "請查看桌面 WestsideStories.log。"
            )
    finally:
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


Worker.write_srt = _write_srt_with_proofreading_and_shadow
Worker.burn = _burn_with_style


if __name__ == "__main__":
    stable_main.main()
