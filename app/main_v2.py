"""Westside Stories 1.1 production entrypoint.

Chinese jobs can run an isolated contextual-ASR challenger before the stable
Whisper path. The challenger is fail-open and short-lived: it never prevents
Whisper from producing usable subtitles and its model memory is released when
the subprocess exits.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import main as stable_main
from main import APP_HOME, Worker, log
from subtitle_style import profile_for_video

stable_main.APP_VERSION = "1.1"

_original_transcribe = Worker.transcribe
_original_write_srt = Worker.write_srt


def _active_memory_scope():
    from dore_subtitle.local_memory import MemoryScope
    return MemoryScope(
        organisation=os.environ.get("WESTSIDE_ORGANISATION", "").strip(),
        speaker=os.environ.get("WESTSIDE_SPEAKER", "").strip(),
        series=os.environ.get("WESTSIDE_SERIES", "").strip(),
    )


def _ensure_contextual_asr_env(self) -> str | None:
    """Prepare a separate challenger environment; failure leaves Whisper intact."""
    py = stable_main.find_python()
    if not py:
        return None
    venv = APP_HOME / "contextual-asr-venv"
    vpy = venv / "bin" / "python"
    try:
        if not vpy.exists():
            self.status.emit("正在準備中文語境辨識引擎…", "Preparing contextual Chinese ASR…")
            subprocess.run([py, "-m", "venv", str(venv)], check=True, text=True, capture_output=True)
        probe = subprocess.run([str(vpy), "-c", "import funasr; print('ok')"], text=True, capture_output=True)
        if probe.returncode != 0:
            self.status.emit("第一次使用：正在安裝中文語境辨識引擎…", "First run: installing contextual Chinese ASR…")
            install = subprocess.run([str(vpy), "-m", "pip", "install", "funasr"], text=True, capture_output=True)
            log("contextual ASR install stdout:\n" + (install.stdout or ""))
            log("contextual ASR install stderr:\n" + (install.stderr or ""))
            if install.returncode != 0:
                return None
        return str(vpy)
    except Exception as exc:
        log(f"contextual ASR environment unavailable: {type(exc).__name__}: {exc}")
        return None


def _challenger_audio_path(self) -> Path:
    """Use the same extracted WAV produced by the stable pipeline when available."""
    audio = getattr(self, "audio", None)
    if audio:
        candidate = Path(audio)
        if candidate.exists():
            return candidate
    for name in ("audio.wav", "extracted_audio.wav", "input.wav"):
        candidate = APP_HOME / name
        if candidate.exists():
            return candidate
    return self.video


def _transcribe_with_contextual_challenger(self, vpy: str, result_json: Path):
    """Run contextual Chinese ASR sequentially, archive evidence, then run Whisper."""
    if self.language in ("zh", "auto"):
        try:
            from dore_subtitle.context_retriever import retrieve_context
            from dore_subtitle.contextual_paraformer import transcribe_challenger

            scope = _active_memory_scope()
            memory_path = Path.home() / "Library" / "Application Support" / "Westside Stories" / "subtitle-memory.json"
            context = retrieve_context(scope=scope, memory_path=memory_path, query="")
            challenger_python = _ensure_contextual_asr_env(self)
            if challenger_python:
                self.status.emit("正在進行中文語境辨識…", "Running contextual Chinese ASR…")
                self.progress.emit(24)
                challenger_input = _challenger_audio_path(self)
                challenger = transcribe_challenger(challenger_python, challenger_input, context=context)
                evidence_dir = APP_HOME / "dore"
                evidence_dir.mkdir(parents=True, exist_ok=True)
                evidence_path = evidence_dir / "last_result.contextual-asr.json"
                evidence_path.write_text(json.dumps({
                    "ok": challenger.ok,
                    "text": challenger.text,
                    "error": challenger.error,
                    "input": str(challenger_input),
                    "context": [{"text": item.text, "score": item.score, "source": item.source} for item in context],
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                if challenger.ok:
                    log(f"contextual ASR challenger completed; chars={len(challenger.text)} context={len(context)} input={challenger_input}")
                else:
                    log("contextual ASR challenger failed; Whisper remains production: " + challenger.error)
        except Exception as exc:
            log(f"contextual ASR challenger isolated failure: {type(exc).__name__}: {exc}")

    _original_transcribe(self, vpy, result_json)


def _write_srt_with_proofreading_and_shadow(self, result_json, srt_path):
    _original_write_srt(self, result_json, srt_path)
    original_text = srt_path.read_text(encoding="utf-8")
    original_path = APP_HOME / "dore" / "last_result.whisper-original.srt"
    try:
        original_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.write_text(original_text, encoding="utf-8", newline="\n")
    except Exception as exc:
        log(f"original SRT archive skipped: {type(exc).__name__}: {exc}")

    try:
        from dore_proofreader import apply_dore_to_srt_text
        corrected, summary = apply_dore_to_srt_text(original_text, scope=_active_memory_scope())
        srt_path.write_text(corrected, encoding="utf-8", newline="\n")
        log(f"Doré proofread: segments={summary.get('segments', 0)} changed={summary.get('changed', 0)}")
    except Exception as exc:
        log(f"Doré proofread unavailable; kept Whisper SRT: {type(exc).__name__}: {exc}")

    try:
        from dore_subtitle.pipeline_bridge import run_shadow_pipeline
        report = run_shadow_pipeline(result_json, APP_HOME)
        if report.get("ok"):
            log(f"dore shadow: ok; segments={report.get('segments', 0)}; suspicions={report.get('suspicions', 0)}")
        else:
            log("dore shadow: skipped; " + str(report.get("error", "unknown")))
    except Exception as exc:
        log(f"dore shadow: isolated failure: {type(exc).__name__}: {exc}")


def _probe_video_size(ffmpeg: str, video: Path) -> tuple[int | None, int | None]:
    ffprobe = str(Path(ffmpeg).with_name("ffprobe"))
    if not Path(ffprobe).is_file():
        return None, None
    try:
        p = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(video)], text=True, capture_output=True, env=stable_main.os.environ.copy())
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
        subtitle_filter = "subtitles=filename='" + str(tmp_path).replace("'", "\\'") + "':force_style='" + force_style + "'"
        log(f"subtitle style: {width}x{height}; {style.ass_force_style()}")
        cmd = [ffmpeg, "-y", "-i", str(self.video), "-vf", subtitle_filter, "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", str(output)]
        p = subprocess.run(cmd, text=True, capture_output=True, env=stable_main.os.environ.copy())
        log("ffmpeg stdout:\n" + (p.stdout or ""))
        log("ffmpeg stderr:\n" + (p.stderr or ""))
        if p.returncode != 0:
            raise RuntimeError("FFmpeg 燒錄失敗。\nFFmpeg burn-in failed.\n\n請查看桌面 WestsideStories.log。")
    finally:
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


Worker.transcribe = _transcribe_with_contextual_challenger
Worker.write_srt = _write_srt_with_proofreading_and_shadow
Worker.burn = _burn_with_style


if __name__ == "__main__":
    stable_main.main()
