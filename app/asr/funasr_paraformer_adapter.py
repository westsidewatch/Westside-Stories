"""Production ASR v2 adapter backed by upstream FunASR Paraformer.

This adapter deliberately delegates speech recognition, VAD and punctuation to
mature upstream models. Westside Stories only supplies dynamic recognition hints.
There is no transcript word-replacement table in this layer.
"""
from __future__ import annotations

from typing import Any

from .adapter import TranscriptionRequest, TranscriptionResult


class FunASRParaformerAdapter:
    name = "funasr-paraformer-zh-contextual"

    def __init__(self) -> None:
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            from funasr import AutoModel
            self._model = AutoModel(
                model="paraformer-zh",
                vad_model="fsmn-vad",
                punc_model="ct-punc",
                disable_update=True,
            )
        return self._model

    @staticmethod
    def _hotwords(request: TranscriptionRequest) -> str:
        # Upstream FunASR consumes contextual bias during recognition.  Keep
        # ordering stable and deduplicate; never mutate recognized text here.
        seen: set[str] = set()
        words: list[str] = []
        for hint in sorted(request.recognition_hints, key=lambda h: h.weight, reverse=True):
            text = hint.text.strip()
            if text and text not in seen:
                seen.add(text)
                words.append(text)
        return " ".join(words)

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        model = self._load()
        hotword = self._hotwords(request)
        kwargs: dict[str, Any] = {
            "input": str(request.audio_path),
            "batch_size_s": 300,
        }
        if hotword:
            kwargs["hotword"] = hotword
        result = model.generate(**kwargs)
        if not result:
            raw: dict[str, Any] = {"text": "", "segments": []}
        else:
            first = result[0] if isinstance(result, list) else result
            raw = dict(first) if isinstance(first, dict) else {"text": str(first)}
        return TranscriptionResult(
            backend=self.name,
            raw=raw,
            hints_requested=len(request.recognition_hints),
            hints_consumed=len(request.recognition_hints) if hotword else 0,
        )

    def release(self) -> None:
        """Release model references after a transcription job."""
        self._model = None
