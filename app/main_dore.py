"""Production entry point: Westside Stories + Doré subtitle proofreading."""
from __future__ import annotations

import traceback
from pathlib import Path

import main as core
from dore_proofreader import apply_dore_to_srt_text


class DoreWorker(core.Worker):
    """Run the existing transcription flow, then require Doré before final output."""

    def proofread_with_dore(self, srt: Path) -> None:
        self.status.emit("多雷正在校對字幕…", "Doré is proofreading subtitles…")
        self.progress.emit(72)
        original = srt.read_text(encoding="utf-8")
        corrected, summary = apply_dore_to_srt_text(original)
        srt.write_text(corrected, encoding="utf-8", newline="\n")
        core.log(
            "Doré proofread: "
            + f"segments={summary.get('segments', 0)} "
            + f"changed={summary.get('changed', 0)}"
        )

    def run(self):
        core.reset_log()
        try:
            srt = self.video.with_suffix(".srt")
            output = self.video.with_name(self.video.stem + "_字幕版.mp4")
            result_json = core.APP_HOME / "last_result.json"

            ffmpeg = core.find_ffmpeg()
            if not ffmpeg:
                raise RuntimeError("找不到 ffmpeg-full。\nffmpeg-full was not found.")
            if not core.has_subtitles_filter(ffmpeg):
                raise RuntimeError(
                    "目前 FFmpeg 沒有 subtitles 濾鏡。\n"
                    "The current FFmpeg build has no subtitles filter."
                )

            self.progress.emit(5)
            if srt.exists() and self.use_existing:
                self.status.emit("使用現有字幕檔。", "Using existing SRT.")
                self.progress.emit(70)
            else:
                vpy = self.ensure_whisper_env()
                self.transcribe(vpy, result_json)
                self.write_srt(result_json, srt)

            # Production contract: every SRT passes through Doré before it is
            # returned to the user or burned into video. A Doré/API failure is
            # explicit; the app never silently claims an unproofread file passed.
            self.proofread_with_dore(srt)

            if self.burn_video:
                self.burn(ffmpeg, srt, output)
                self.progress.emit(100)
                self.status.emit("完成。", "Completed.")
                self.finished.emit(str(srt), str(output))
            else:
                self.progress.emit(100)
                self.status.emit("字幕已完成。", "Subtitle completed.")
                self.finished.emit(str(srt), "")
        except Exception as exc:
            core.log("EXCEPTION:\n" + traceback.format_exc())
            self.failed.emit(str(exc))


# MainWindow resolves Worker from the core module at runtime.
core.Worker = DoreWorker

if __name__ == "__main__":
    core.main()
