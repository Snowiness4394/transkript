"""Transcription engine — faster-whisper wrapper."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

from transkript.audio import SAMPLE_RATE, CHANNELS


@dataclass
class Segment:
    """A single transcription segment with timestamps."""
    start: float
    end: float
    text: str


@dataclass
class TranscribeSettings:
    """Configurable transcription settings for performance tuning."""
    beam_size: int = 5
    vad_filter: bool = False
    condition_on_previous_text: bool = True
    compute_type: str = "default"
    cpu_threads: int = 0

    @classmethod
    def low_spec(cls) -> TranscribeSettings:
        return cls(
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            compute_type="int8",
            cpu_threads=2,
        )

    @classmethod
    def high_spec(cls) -> TranscribeSettings:
        return cls(
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=True,
            compute_type="default",
            cpu_threads=0,
        )


class Transcriber:
    """Wraps faster-whisper for local transcription."""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "cpu",
        settings: TranscribeSettings | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.settings = settings or TranscribeSettings()
        self._model: WhisperModel | None = None

    def load(self) -> None:
        kwargs: dict = {"device": self.device}
        if self.settings.compute_type != "default":
            kwargs["compute_type"] = self.settings.compute_type
        if self.settings.cpu_threads:
            kwargs["cpu_threads"] = self.settings.cpu_threads
        self._model = WhisperModel(self.model_name, **kwargs)

    def load_new(self, model_name: str) -> None:
        self.model_name = model_name
        self.load()

    def apply_settings(self, settings: TranscribeSettings) -> None:
        self.settings = settings

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def save_wav(self, audio: np.ndarray, path: Path) -> None:
        audio_int16 = (audio * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> list[Segment]:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        kwargs: dict = {
            "beam_size": self.settings.beam_size,
            "vad_filter": self.settings.vad_filter,
            "condition_on_previous_text": self.settings.condition_on_previous_text,
        }
        if language:
            kwargs["language"] = language

        segments, info = self._model.transcribe(audio, **kwargs)

        result = []
        for seg in segments:
            result.append(Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
            ))

        return result, info

    def format_timestamp(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def save_transcript(
        self,
        segments: list[Segment],
        output_path: Path,
        duration: float,
        language: str = "unknown",
    ) -> None:
        from datetime import datetime

        lines = [
            "Meeting Transcript",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {self.format_timestamp(duration)}",
            f"Language: {language} (auto-detected)",
            "",
        ]

        for seg in segments:
            timestamp = self.format_timestamp(seg.start)
            lines.append(f"[{timestamp}] {seg.text}")

        output_path.write_text("\n".join(lines), encoding="utf-8")
