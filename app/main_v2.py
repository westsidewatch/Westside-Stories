"""Westside Stories 1.1 production entrypoint.

Keeps the stable main.py subtitle path intact while attaching Doré v2 as a
fail-open, post-ASR shadow observer. Doré cannot block or mutate SRT output.
Release-only wiring also applies the 1.1 version label and adaptive burn-in
styles without changing the portable SRT itself.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import main as stable_main
from main import APP_HOME, Worker, log
from subtitle_style import profile_for_video

# Release identity is owned by the 1.1 entrypoint so the stable 1.0 module can
# remain untouched while every UI/log lookup observes the current version.
stable_main.APP_VERSION = "1.1"

_original_write_srt = Worker.write_srt


def _write_srt_with_shadow(self, result_json, srt_path):
    _original_write_srt(self, result_json, srt_path)
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


Worker.write_srt = _write_srt_with_shadow
Worker.burn = _burn_with_style


if __name__ == "__main__":
    stable_main.main()
