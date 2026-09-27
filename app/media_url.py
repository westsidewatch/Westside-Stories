"""Remote media ingestion for Westside Stories.

Accepts a public video URL and downloads audio only. No video render/download is
needed for transcription benchmarks. yt-dlp is invoked as a subprocess so this
module stays independent from the GUI and ASR engines.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def is_media_url(value: str) -> bool:
    try:
        parsed = urlparse((value or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def find_ytdlp() -> str | None:
    return shutil.which("yt-dlp")


def download_audio(url: str, destination: Path, *, timeout: int = 3600) -> Path:
    """Download best available audio and normalize to mono 16 kHz WAV for ASR."""
    tool = find_ytdlp()
    if not tool:
        raise RuntimeError("yt-dlp is not installed")
    destination.mkdir(parents=True, exist_ok=True)
    template = destination / "source.%(ext)s"
    cmd = [
        tool,
        "--no-playlist",
        "--no-write-thumbnail",
        "--no-write-info-json",
        "-f", "bestaudio/best",
        "-x",
        "--audio-format", "wav",
        "--postprocessor-args", "ffmpeg:-ac 1 -ar 16000",
        "-o", str(template),
        url,
    ]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "yt-dlp failed").strip())
    wavs = sorted(destination.glob("source*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not wavs:
        raise RuntimeError("yt-dlp completed without an audio file")
    return wavs[0]
