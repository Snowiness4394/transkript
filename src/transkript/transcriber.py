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


class Transcriber:
    """Wraps faster-whisper for local transcription."""

    def __init__(self, model_name: str = "base", device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._model: WhisperModel | None = None

    def load(self) -> None:
        """Load the Whisper model. Downloads on first run (~74MB for base)."""
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
        )

    def load_new(self, model_name: str) -> None:
        """Load a different model, replacing the current one."""
        self.model_name = model_name
        self._model = WhisperModel(
            model_name,
            device=self.device,
        )

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def save_wav(self, audio: np.ndarray, path: Path) -> None:
        """Save a float32 numpy array as a WAV file."""
        audio_int16 = (audio * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> list[Segment]:
        """Transcribe a float32 numpy array and return segments with timestamps."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        kwargs = {"beam_size": 5}
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
        """Format seconds as HH:MM:SS."""
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
        """Save segments to a .txt file with timestamps."""
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
