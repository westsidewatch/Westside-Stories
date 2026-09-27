"""Current Westside Stories ASR backend: MLX Whisper.

This adapter preserves the existing recognizer and provides a safe place to
consume recognition context when the installed mlx-whisper API supports it.
Unsupported hints are ignored rather than becoming a runtime dependency.
"""
from __future__ import annotations

from typing import Any

from .adapter import RecognitionHint, TranscriptionRequest, TranscriptionResult


class MLXWhisperAdapter:
    name = "mlx-whisper"

    def __init__(self, model: str = "mlx-community/whisper-turbo") -> None:
        self.model = model

    @staticmethod
    def _prompt(hints: tuple[RecognitionHint, ...]) -> str:
        # Keep context bounded upstream; here we only serialize confirmed hints.
        return "、".join(item.text.strip() for item in hints if item.text.strip())

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        import mlx_whisper

        kwargs: dict[str, Any] = {}
        if request.language:
            kwargs["language"] = request.language

        # mlx-whisper versions differ in supported decoding kwargs. Preserve the
        # stable path first; recognition hints remain advisory until capability
        # detection is wired against the installed version.
        raw = mlx_whisper.transcribe(
            str(request.audio_path),
            path_or_hf_repo=self.model,
            **kwargs,
        )
        return TranscriptionResult(
            backend=self.name,
            raw=raw,
            hints_requested=len(request.recognition_hints),
            hints_consumed=0,
        )
