"""Westside Stories production entrypoint with contextual Chinese ASR v2."""
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

stable_main.APP_VERSION = "1.2"

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


def _asr_audio_path(self) -> Path:
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


def _transcribe_production(self, vpy: str, result_json: Path):
    if self.language in ("zh", "auto"):
        try:
            from asr.church_context import load_context_terms
            from dore_subtitle.context_retriever import CorpusTerm, retrieve_context
            from dore_subtitle.contextual_paraformer import transcribe_challenger
            scope = _active_memory_scope()
            memory_path = Path.home() / "Library" / "Application Support" / "Westside Stories" / "subtitle-memory.json"
            corpus = [CorpusTerm(text=term, evidence="bible/church corpus", weight=1.0) for term in load_context_terms(APP_HOME)]
            context = retrieve_context(scope=scope, memory_path=memory_path, corpus_terms=corpus, query=os.environ.get("WESTSIDE_SERMON_CONTEXT", "").strip(), limit=64)
            asr_python = _ensure_contextual_asr_env(self)
            if asr_python:
                self.status.emit("正在進行中文語境辨識…", "Running contextual Chinese ASR…")
                self.progress.emit(30)
                result = transcribe_challenger(asr_python, _asr_audio_path(self), context=context)
                segments = result.raw.get("segments") if result.ok else None
                if result.ok and segments:
                    result_json.write_text(json.dumps({"text": result.text, "segments": segments, "backend": "funasr-paraformer-zh-contextual", "context_terms": len(context)}, ensure_ascii=False), encoding="utf-8")
                    log(f"production contextual ASR completed; segments={len(segments)} chars={len(result.text)} context={len(context)} corpus={len(corpus)}")
                    return
                log("production contextual ASR unavailable; falling back to Whisper: " + (result.error or "no timestamped segments"))
        except Exception as exc:
            log(f"production contextual ASR failure; falling back to Whisper: {type(exc).__name__}: {exc}")
    _original_transcribe(self, vpy, result_json)


def _write_srt_production(self, result_json, srt_path):
    _original_write_srt(self, result_json, srt_path)


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
    self.status.emit("正在使用 Mac 硬體快速燒錄字幕…", "Burning subtitles with Mac hardware acceleration…")
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

        # Subtitle rendering still happens in the filter graph, but final H.264 encoding
        # is delegated to Apple's VideoToolbox hardware encoder instead of libx264 CPU.
        cmd = [ffmpeg, "-y", "-i", str(self.video), "-vf", subtitle_filter,
               "-c:v", "h264_videotoolbox", "-q:v", "65", "-allow_sw", "1",
               "-c:a", "copy", "-movflags", "+faststart", str(output)]
        p = subprocess.run(cmd, text=True, capture_output=True, env=stable_main.os.environ.copy())
        log("ffmpeg stdout:\n" + (p.stdout or ""))
        log("ffmpeg stderr:\n" + (p.stderr or ""))
        if p.returncode != 0:
            raise RuntimeError("FFmpeg 硬體燒錄失敗。\nFFmpeg hardware burn-in failed.\n\n請查看桌面 WestsideStories.log。")
    finally:
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


Worker.transcribe = _transcribe_production
Worker.write_srt = _write_srt_production
Worker.burn = _burn_with_style

if __name__ == "__main__":
    stable_main.main()
