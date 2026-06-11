"""Textual application — single-screen meeting transcriber."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Select, Static, Switch

from transkript.audio import (
    find_loopback_device,
    int16_to_float32,
    list_input_devices,
    list_output_devices,
    record_mixed,
    record_mixed_int16,
)
from transkript.transcriber import Transcriber, TranscribeSettings

LOG_PATH = Path(__file__).parent.parent.parent / "transkript.log"

logging.basicConfig(
    filename=str(LOG_PATH),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("transkript")

LANGUAGES = [
    ("Auto-detect", ""),
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Russian", "ru"),
    ("Japanese", "ja"),
    ("Chinese", "zh"),
    ("Korean", "ko"),
    ("Arabic", "ar"),
    ("Hindi", "hi"),
    ("Dutch", "nl"),
    ("Swedish", "sv"),
    ("Polish", "pl"),
    ("Turkish", "tr"),
    ("Vietnamese", "vi"),
    ("Thai", "th"),
    ("Indonesian", "id"),
]

MODELS = [
    ("tiny (39MB)", "tiny"),
    ("base (74MB)", "base"),
    ("small (244MB)", "small"),
    ("medium (769MB)", "medium"),
    ("large-v3 (1.5GB)", "large-v3"),
]

AUDIO_BUFFER_MAXLEN = 120


class TranskriptApp(App):
    """A local meeting transcriber — records mic + system audio, transcribes with Whisper."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "transkript"

    state: reactive[str] = reactive("idle")
    duration: reactive[float] = reactive(0.0)
    status_text: reactive[str] = reactive("Ready")
    last_file: reactive[str] = reactive("")
    last_dir: reactive[str] = reactive("")
    detected_language: reactive[str] = reactive("")
    low_spec: reactive[bool] = reactive(True)

    def __init__(self, model_name: str = "base", output_dir: str = "./transcripts") -> None:
        super().__init__()
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.transcriber = Transcriber(model_name=model_name, settings=TranscribeSettings.low_spec())
        self._recording_start: float = 0.0
        self._all_segments: list = []
        self._loopback_device: int | None = None
        self._audio_buffer: deque[np.ndarray] = deque(maxlen=AUDIO_BUFFER_MAXLEN)
        self._recording_thread: threading.Thread | None = None
        self._stop_recording_event = threading.Event()

    def _on_worker_error(self, worker, exception) -> None:
        log.error("Worker error (%s): %s", worker.worker_name, exception)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="root"):
            with Vertical(id="main-content"):
                yield Center(Button("Start Recording", id="record-btn", variant="success"))
                yield Static("Ready", id="status")
                yield Static("", id="duration-display")
                yield Static("", id="file-info")
                with Horizontal(id="file-links"):
                    yield Button("Open File", id="open-file-btn", variant="primary")
                    yield Button("Open Folder", id="open-folder-btn", variant="primary")
            with Vertical(id="settings-panel"):
                yield Static("Mic", id="mic-label")
                yield Select([], id="mic-select", prompt="Loading devices...")
                yield Static("Output", id="output-label")
                yield Select([], id="output-select", prompt="Loading devices...")
                yield Static("Language", id="lang-label")
                yield Select(LANGUAGES, id="lang-select", prompt="Auto-detect")
                yield Static("Model", id="model-label")
                yield Select(MODELS, id="model-select", prompt="base")
                with Horizontal(id="low-spec-row"):
                    yield Switch(id="low-spec-switch", value=True)
                    yield Static("Low-spec mode", id="low-spec-label")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#open-file-btn").display = False
        self.query_one("#open-folder-btn").display = False
        self.query_one("#duration-display").display = False

        mic_devices = list_input_devices()
        output_devices = list_output_devices()

        mic_options = [(d["name"], d["index"]) for d in mic_devices]
        if not mic_options:
            mic_options = [("No microphone found", -1)]

        output_options = [(d["name"], d["index"]) for d in output_devices]
        if not output_options:
            output_options = [("No output device found", -1)]

        self._loopback_device = find_loopback_device()

        mic_select = self.query_one("#mic-select", Select)
        mic_select.set_options(mic_options)
        if mic_options:
            mic_select.value = mic_options[0][1]

        output_select = self.query_one("#output-select", Select)
        output_select.set_options(output_options)
        if output_options:
            output_select.value = output_options[0][1]

        self.query_one("#lang-select", Select).value = ""

        if self.low_spec and self.model_name not in ("tiny",):
            self.model_name = "tiny"
            self.query_one("#model-select", Select).value = "tiny"
        else:
            self.query_one("#model-select", Select).value = self.model_name

        self._load_model()

    def _get_settings(self) -> TranscribeSettings:
        if self.low_spec:
            return TranscribeSettings.low_spec()
        return TranscribeSettings.high_spec()

    def _load_model(self) -> None:
        self.state = "loading"
        self.status_text = f"Loading model ({self.model_name})..."
        self.query_one("#status").update(self.status_text)
        self.transcriber.apply_settings(self._get_settings())
        self.run_worker(self._load_model_worker, exclusive=True, thread=True)

    def _load_model_worker(self) -> None:
        self.transcriber.load()
        self.call_from_thread(self._on_model_loaded)

    def _on_model_loaded(self) -> None:
        self.state = "idle"
        self.status_text = "Ready"
        self.query_one("#status").update(self.status_text)
        self.query_one("#model-select", Select).disabled = False
        self.query_one("#record-btn").disabled = False

    @on(Button.Pressed, "#record-btn")
    def handle_record_button(self, event: Button.Pressed) -> None:
        if self.state in ("idle", "done"):
            self._start_recording()
        elif self.state == "recording":
            self._stop_recording()

    @on(Button.Pressed, "#open-file-btn")
    def handle_open_file(self, event: Button.Pressed) -> None:
        if self.last_file:
            if hasattr(os, 'startfile'):
                os.startfile(self.last_file)
            else:
                subprocess.run(["xdg-open", self.last_file], check=False)

    @on(Button.Pressed, "#open-folder-btn")
    def handle_open_folder(self, event: Button.Pressed) -> None:
        if self.last_dir:
            if hasattr(os, 'startfile'):
                os.startfile(self.last_dir)
            else:
                subprocess.run(["xdg-open", self.last_dir], check=False)

    @on(Switch.Changed, "#low-spec-switch")
    def on_low_spec_changed(self, event: Switch.Changed) -> None:
        self.low_spec = event.value
        if self.low_spec:
            self.transcriber.apply_settings(TranscribeSettings.low_spec())
            if self.model_name != "tiny":
                self._load_new_model("tiny")
        else:
            self.transcriber.apply_settings(TranscribeSettings.high_spec())
            if self.model_name == "tiny":
                self._load_new_model("base")

    def _start_recording(self) -> None:
        if not self.transcriber.is_loaded:
            self.status_text = "Model still loading, please wait..."
            self.query_one("#status").update(self.status_text)
            return

        self.state = "recording"
        self._recording_start = time.time()
        self._all_segments = []
        self.duration = 0.0
        self.detected_language = ""
        self._audio_buffer.clear()
        self._stop_recording_event.clear()

        btn = self.query_one("#record-btn")
        btn.label = "Stop Recording"
        btn.variant = "error"

        self.status_text = "Recording..."
        self.query_one("#status").update(self.status_text)

        self.query_one("#low-spec-switch", Switch).disabled = True

        self.query_one("#duration-display").display = False
        self.query_one("#duration-display").update("Duration: 00:00:00")
        self.query_one("#open-file-btn").display = False
        self.query_one("#open-folder-btn").display = False
        self.query_one("#file-info").update("")
        self.last_file = ""
        self.last_dir = ""

        self._recording_thread = threading.Thread(
            target=self._record_audio_thread, daemon=True
        )
        self._recording_thread.start()

        self.run_worker(self._transcription_loop, exclusive=True, thread=True)

    def _record_audio_thread(self) -> None:
        mic_device = self.query_one("#mic-select", Select).value
        output_device = self.query_one("#output-select", Select).value

        if mic_device == Select.BLANK:
            mic_device = None
        if output_device == Select.BLANK:
            output_device = None

        loopback_device = self._loopback_device
        record_duration = 1

        while not self._stop_recording_event.is_set():
            try:
                if self.low_spec:
                    audio = record_mixed_int16(record_duration, mic_device, loopback_device)
                else:
                    audio = record_mixed(record_duration, mic_device, loopback_device)
                if not self._stop_recording_event.is_set():
                    self._audio_buffer.append(audio)
            except Exception as e:
                if self._stop_recording_event.is_set():
                    log.debug("Recording stopped cleanly during device wait")
                    break
                log.warning("Recording chunk failed: %s", e)
                time.sleep(0.1)

    def _stop_recording(self) -> None:
        log.info("Stopping recording...")
        self.state = "transcribing"
        self.status_text = "Saving transcript..."
        self.query_one("#status").update(self.status_text)

        btn = self.query_one("#record-btn")
        btn.label = "Transcribing..."
        btn.variant = "warning"
        btn.disabled = True

        self._stop_recording_event.set()
        if self._recording_thread:
            self._recording_thread.join(timeout=2)
            if self._recording_thread.is_alive():
                log.warning("Recording thread did not stop in time, continuing anyway")
            self._recording_thread = None
        log.info("Recording stopped")

    def _transcription_loop(self) -> None:
        lang_value = self.query_one("#lang-select", Select).value
        language = lang_value if lang_value else None

        chunk_num = 0
        chunk_duration = 30
        sample_rate = 16000

        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            while self.state == "recording" or self._audio_buffer:
                if len(self._audio_buffer) < chunk_duration and self.state == "recording":
                    time.sleep(0.5)
                    continue

                audio_chunks = []
                total_samples = 0
                target_samples = chunk_duration * sample_rate

                while self._audio_buffer and total_samples < target_samples:
                    chunk = self._audio_buffer.popleft()
                    audio_chunks.append(chunk)
                    total_samples += len(chunk)

                if not audio_chunks:
                    if self.state != "recording":
                        break
                    time.sleep(0.5)
                    continue

                audio = np.concatenate(audio_chunks)

                if self.low_spec:
                    audio = int16_to_float32(audio)

                chunk_num += 1
                self.call_from_thread(
                    self._update_status, f"Transcribing chunk {chunk_num}..."
                )

                segments, info = self.transcriber.transcribe(audio, language=language)

                if info.language and not self.detected_language:
                    self.detected_language = info.language
                    self.call_from_thread(
                        self._update_status,
                        f"Recording... (detected: {info.language})"
                    )

                time_offset = (chunk_num - 1) * chunk_duration
                for seg in segments:
                    self._all_segments.append(
                        type("Segment", (), {
                            "start": seg.start + time_offset,
                            "end": seg.end + time_offset,
                            "text": seg.text,
                        })()
                    )

                self.call_from_thread(self._update_duration)
        except Exception as e:
            log.error("Transcription loop error: %s", e, exc_info=True)

        self._save_transcript()

    def _update_status(self, text: str) -> None:
        self.status_text = text
        self.query_one("#status").update(text)

    def _update_duration(self) -> None:
        elapsed = time.time() - self._recording_start
        self.duration = elapsed
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        secs = int(elapsed % 60)
        duration_widget = self.query_one("#duration-display")
        duration_widget.display = True
        duration_widget.update(f"Duration: {hours:02d}:{minutes:02d}:{secs:02d}")

    def _save_transcript(self) -> None:
        session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"meeting_{session_id}.txt"
        filepath = self.output_dir / filename

        elapsed = time.time() - self._recording_start

        self.transcriber.save_transcript(
            segments=self._all_segments,
            output_path=filepath,
            duration=elapsed,
            language=self.detected_language or "unknown",
        )

        self.call_from_thread(self._on_save_complete, str(filepath))

    def _on_save_complete(self, filepath: str) -> None:
        if self.state != "transcribing":
            return

        self.state = "done"
        self.last_file = filepath
        self.last_dir = str(Path(filepath).parent)

        btn = self.query_one("#record-btn")
        btn.label = "Start Recording"
        btn.variant = "success"
        btn.disabled = False

        self.query_one("#low-spec-switch", Switch).disabled = False

        self.status_text = "Complete"
        self.query_one("#status").update(self.status_text)

        self.query_one("#file-info").update(f"Transcript: {Path(filepath).name}")

        self.query_one("#open-file-btn").display = True
        self.query_one("#open-folder-btn").display = True

    @on(Select.Changed, "#mic-select")
    def on_mic_changed(self, event: Select.Changed) -> None:
        pass

    @on(Select.Changed, "#output-select")
    def on_output_changed(self, event: Select.Changed) -> None:
        if event.value != Select.BLANK:
            self._loopback_device = find_loopback_device()

    @on(Select.Changed, "#model-select")
    def on_model_changed(self, event: Select.Changed) -> None:
        if event.value != Select.BLANK and event.value != self.model_name:
            self._load_new_model(event.value)

    def _load_new_model(self, model_name: str) -> None:
        if self.state == "recording":
            return

        self.state = "loading"
        self.model_name = model_name
        self.status_text = f"Loading model ({model_name})..."
        self.query_one("#status").update(self.status_text)

        self.query_one("#model-select", Select).disabled = True
        self.query_one("#record-btn").disabled = True

        self.transcriber.apply_settings(self._get_settings())
        self.run_worker(self._load_new_model_worker, exclusive=True, thread=True)

    def _load_new_model_worker(self) -> None:
        self.transcriber.load_new(self.model_name)
        self.call_from_thread(self._on_model_loaded)
