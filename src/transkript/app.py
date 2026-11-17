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
from typing import Any, cast

import numpy as np

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
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

AUDIO_BUFFER_MAXLEN = 300  # ~5 min of 1s chunks


class TranskriptApp(App):
    """A local meeting transcriber — records mic + system audio, transcribes with Whisper."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "transkript"
    BINDINGS = [
        Binding("enter", "toggle_recording", "Start/Stop"),
        Binding("q", "quit", "Quit"),
    ]

    state: reactive[str] = reactive("idle")
    status_text: reactive[str] = reactive("Ready")
    last_file: reactive[str] = reactive("")
    last_dir: reactive[str] = reactive("")
    detected_language: reactive[str] = reactive("")
    low_spec: reactive[bool] = reactive(False)

    def __init__(
        self,
        model_name: str = "base",
        output_dir: str = "./transcripts",
        low_spec: bool = False,
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.low_spec = low_spec
        settings = TranscribeSettings.low_spec() if low_spec else TranscribeSettings.high_spec()
        self.transcriber = Transcriber(model_name=model_name, settings=settings)
        self._recording_start: float = 0.0
        self._recording_seconds: int = 0
        self._all_segments: list = []
        self._loopback_device: int | None = None
        self._audio_buffer: deque[np.ndarray] = deque(maxlen=AUDIO_BUFFER_MAXLEN)
        self._recording_thread: threading.Thread | None = None
        self._stop_recording_event = threading.Event()
        self._duration_timer = None
        self._model_revert_name: str | None = None
        self._spec_revert: tuple[bool, TranscribeSettings] | None = None
        self._recording_limit_reached: bool = False
        self._transcribe_language: str | None = None

    def _enable_controls(self) -> None:
        btn = self.query_one("#record-btn", Button)
        btn.label = "Start Recording"
        btn.variant = "success"
        btn.disabled = False
        self.query_one("#model-select", Select).disabled = False
        self.query_one("#low-spec-switch", Switch).disabled = False

    def _on_worker_failed(self, message: str) -> None:
        """Restore a usable UI after a worker fails (load, switch or transcription)."""
        log.error(message)
        if self.state == "loading" and self._model_revert_name:
            reverted = self._model_revert_name
            self.model_name = reverted
            self.transcriber.model_name = reverted
            self.query_one("#model-select", Select).value = reverted
        self._model_revert_name = None
        if self._spec_revert:
            previous_low_spec, previous_settings = self._spec_revert
            self.low_spec = previous_low_spec
            self.transcriber.apply_settings(previous_settings)
            self.query_one("#low-spec-switch", Switch).value = previous_low_spec
        self._spec_revert = None
        self.state = "idle"
        self._update_status(message)
        self.query_one("#file-info").update("")
        self._enable_controls()

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
                    yield Switch(id="low-spec-switch", value=self.low_spec)
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
        self.query_one("#model-select", Select).value = self.model_name

        self._load_model()

    def _get_settings(self) -> TranscribeSettings:
        if self.low_spec:
            return TranscribeSettings.low_spec()
        return TranscribeSettings.high_spec()

    def _load_model(self) -> None:
        self.state = "loading"
        self.status_text = f"Loading model ({self.model_name})..."
        self.query_one("#status", Static).update(self.status_text)
        self.transcriber.apply_settings(self._get_settings())
        self.query_one("#record-btn", Button).disabled = True
        self.query_one("#model-select", Select).disabled = True
        self.query_one("#low-spec-switch", Switch).disabled = True
        self.run_worker(
            self._load_model_worker, exclusive=True, thread=True, exit_on_error=False
        )

    def _load_model_worker(self) -> None:
        try:
            self.transcriber.load()
        except Exception as exc:
            log.exception("Model load failed")
            self.call_from_thread(
                self._on_worker_failed,
                f"Failed to load model {self.model_name}: {exc}",
            )
            return
        self.call_from_thread(self._on_model_loaded)

    def _on_model_loaded(self) -> None:
        self.state = "idle"
        self.status_text = "Ready"
        self.query_one("#status", Static).update(self.status_text)
        self._model_revert_name = None
        self._spec_revert = None
        self._enable_controls()

    @on(Button.Pressed, "#record-btn")
    def handle_record_button(self, event: Button.Pressed) -> None:
        self.action_toggle_recording()

    def action_toggle_recording(self) -> None:
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
        if self.state not in ("idle", "done") or event.value == self.low_spec:
            return

        self._spec_revert = (self.low_spec, self.transcriber.settings)
        self.low_spec = event.value
        self.transcriber.apply_settings(self._get_settings())

        new_model = self.model_name
        if event.value and new_model == "base":
            new_model = "tiny"
        elif not event.value and new_model == "tiny":
            new_model = "base"

        # compute_type and cpu_threads are fixed when the model is constructed,
        # so a mode switch must always reload — even if the model name is unchanged.
        self._load_new_model(new_model)
        self.query_one("#model-select", Select).value = new_model

    # ── Recording phase ──────────────────────────────────────────────

    def _start_recording(self) -> None:
        if not self.transcriber.is_loaded:
            self.status_text = "Model still loading, please wait..."
            self.query_one("#status", Static).update(self.status_text)
            return

        mic_device = self.query_one("#mic-select", Select).value
        if not isinstance(mic_device, int) or mic_device < 0:
            self._update_status("No microphone found — select an input device")
            return

        self.state = "recording"
        self._recording_limit_reached = False
        self._recording_start = time.time()
        self._recording_seconds = 0
        self._all_segments = []
        self.detected_language = ""
        self._audio_buffer.clear()
        self._stop_recording_event.clear()

        btn = self.query_one("#record-btn")
        btn.label = "Stop Recording"
        btn.variant = "error"

        self.status_text = "Recording..."
        self.query_one("#status", Static).update(self.status_text)

        self.query_one("#low-spec-switch", Switch).disabled = True
        self.query_one("#model-select", Select).disabled = True

        # Show and reset duration
        dur = self.query_one("#duration-display")
        dur.display = True
        dur.update("Duration: 00:00:00")

        self.query_one("#open-file-btn").display = False
        self.query_one("#open-folder-btn").display = False
        self.query_one("#file-info").update("")
        self.last_file = ""
        self.last_dir = ""

        # Start duration timer (ticks every second on main thread)
        self._duration_timer = self.set_interval(1, self._tick_duration)

        # Start recording thread
        self._recording_thread = threading.Thread(
            target=self._record_audio_thread, daemon=True
        )
        self._recording_thread.start()

    def _tick_duration(self) -> None:
        """Called every second during recording to update the duration label."""
        self._recording_seconds += 1
        h = self._recording_seconds // 3600
        m = (self._recording_seconds % 3600) // 60
        s = self._recording_seconds % 60
        self.query_one("#duration-display").update(f"Duration: {h:02d}:{m:02d}:{s:02d}")

    def _record_audio_thread(self) -> None:
        """Background thread that records audio continuously into buffer."""
        mic_device = self.query_one("#mic-select", Select).value
        output_device = self.query_one("#output-select", Select).value

        if not isinstance(mic_device, int) or mic_device < 0:
            mic_device = None
        if not isinstance(output_device, int) or output_device < 0:
            output_device = None

        loopback_device = self._loopback_device
        record_duration = 1

        while not self._stop_recording_event.is_set():
            try:
                if self.low_spec:
                    audio = record_mixed_int16(record_duration, mic_device, loopback_device)
                else:
                    audio = record_mixed(record_duration, mic_device, loopback_device)
            except Exception as e:
                if self._stop_recording_event.is_set():
                    log.debug("Recording stopped cleanly during device wait")
                    break
                log.warning("Recording chunk failed: %s", e)
                time.sleep(0.1)
                continue

            # Keep the chunk that was in flight when Stop was pressed.
            self._audio_buffer.append(audio)

            if len(self._audio_buffer) >= AUDIO_BUFFER_MAXLEN:
                self._recording_limit_reached = True
                self._stop_recording_event.set()
                log.warning("Maximum recording length reached; stopping recording")
                self.call_from_thread(self._stop_recording)

    # ── Stop recording → Transcription phase ─────────────────────────

    def _stop_recording(self) -> None:
        if self.state != "recording":
            return
        log.info("Stopping recording (%ds of audio)", self._recording_seconds)

        # Stop duration timer
        if self._duration_timer:
            self._duration_timer.stop()
            self._duration_timer = None

        # Stop recording thread
        self._stop_recording_event.set()
        if self._recording_thread:
            self._recording_thread.join(timeout=2)
            if self._recording_thread.is_alive():
                log.warning("Recording thread did not stop in time")
            self._recording_thread = None

        self.state = "transcribing"

        btn = self.query_one("#record-btn")
        btn.label = "Transcribing..."
        btn.variant = "warning"
        btn.disabled = True

        # Launch transcription worker (after stop, not concurrent)
        lang_value = self.query_one("#lang-select", Select).value
        self._transcribe_language = lang_value if isinstance(lang_value, str) else None
        self.run_worker(
            self._transcribe_after_stop, exclusive=True, thread=True, exit_on_error=False
        )

    def _transcribe_after_stop(self) -> None:
        """Transcribe all recorded audio after recording has stopped."""
        try:
            chunk_duration = 30
            sample_rate = 16000

            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Drain the buffer
            audio_chunks = []
            while self._audio_buffer:
                audio_chunks.append(self._audio_buffer.popleft())

            if not audio_chunks:
                log.warning("No audio to transcribe")
                self.call_from_thread(self._on_save_complete_no_file)
                return

            # Split into 30s chunks and transcribe sequentially
            full_audio = np.concatenate(audio_chunks)
            total_samples = len(full_audio)
            samples_per_chunk = chunk_duration * sample_rate
            chunk_num = 0
            total_chunks = max(1, (total_samples + samples_per_chunk - 1) // samples_per_chunk)

            language: str | None = self._transcribe_language

            try:
                offset = 0
                while offset < total_samples:
                    chunk = full_audio[offset : offset + samples_per_chunk]
                    offset += samples_per_chunk

                    # Convert int16 to float32 if needed
                    if self.low_spec:
                        chunk = int16_to_float32(chunk)

                    chunk_num += 1
                    self.call_from_thread(
                        self._update_status,
                        f"Transcribing chunk {chunk_num}/{total_chunks}...",
                    )

                    segments, info = self.transcriber.transcribe(chunk, language=language)

                    if info.language and not self.detected_language:
                        self.detected_language = info.language

                    time_offset = (chunk_num - 1) * chunk_duration
                    for seg in segments:
                        self._all_segments.append(
                            type("Segment", (), {
                                "start": seg.start + time_offset,
                                "end": seg.end + time_offset,
                                "text": seg.text,
                            })()
                        )

                    log.info("Chunk %d/%d: %d segments, total so far: %d",
                             chunk_num, total_chunks, len(segments), len(self._all_segments))
            except Exception as e:
                log.error("Transcription error: %s", e, exc_info=True)

            log.info("Transcription complete: %d total segments", len(self._all_segments))
            self._save_transcript()
        except Exception as exc:
            log.exception("Transcription failed")
            self.call_from_thread(self._on_worker_failed, f"Transcription failed: {exc}")

    def _update_status(self, text: str) -> None:
        self.status_text = text
        self.query_one("#status", Static).update(text)

    def _save_transcript(self) -> None:
        session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"meeting_{session_id}.txt"
        filepath = self.output_dir / filename

        self.transcriber.save_transcript(
            segments=self._all_segments,
            output_path=filepath,
            duration=float(self._recording_seconds),
            language=self.detected_language or "unknown",
            language_was_explicit=self._transcribe_language is not None,
        )

        self.call_from_thread(self._on_save_complete, str(filepath))

    def _on_save_complete(self, filepath: str) -> None:
        if self.state != "transcribing":
            return

        self.state = "done"
        self.last_file = filepath
        self.last_dir = str(Path(filepath).parent)

        self._enable_controls()

        self.status_text = (
            "Complete — maximum length reached"
            if self._recording_limit_reached
            else "Complete"
        )
        self.query_one("#status", Static).update(self.status_text)

        self.query_one("#file-info").update(f"Transcript: {Path(filepath).name}")

        self.query_one("#open-file-btn").display = True
        self.query_one("#open-folder-btn").display = True

    def _on_save_complete_no_file(self) -> None:
        """Called when there was no audio to transcribe."""
        if self.state != "transcribing":
            return

        self.state = "idle"

        self._enable_controls()

        self.status_text = "No audio recorded"
        self.query_one("#status", Static).update(self.status_text)

    # ── Device / model changes ───────────────────────────────────────

    @on(Select.Changed, "#mic-select")
    def on_mic_changed(self, event: Select.Changed) -> None:
        pass

    @on(Select.Changed, "#output-select")
    def on_output_changed(self, event: Select.Changed) -> None:
        if event.value != Select.BLANK:
            self._loopback_device = find_loopback_device()

    @on(Select.Changed, "#model-select")
    def on_model_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK or event.value == self.model_name:
            return
        if self.state not in ("idle", "done"):
            select_widget = cast(Any, event.select)
            select_widget.value = self.model_name
            self._update_status("Cannot change model while recording or transcribing")
            return
        self._load_new_model(cast(str, event.value))

    def _load_new_model(self, model_name: str) -> None:
        if self.state not in ("idle", "done"):
            return

        self._model_revert_name = self.model_name
        self.state = "loading"
        self.model_name = model_name
        self.status_text = f"Loading model ({model_name})..."
        self.query_one("#status", Static).update(self.status_text)

        self.query_one("#model-select", Select).disabled = True
        self.query_one("#record-btn", Button).disabled = True
        self.query_one("#low-spec-switch", Switch).disabled = True

        self.transcriber.apply_settings(self._get_settings())
        self.run_worker(
            self._load_new_model_worker,
            exclusive=True,
            thread=True,
            exit_on_error=False,
        )

    def _load_new_model_worker(self) -> None:
        try:
            self.transcriber.load_new(self.model_name)
        except Exception as exc:
            log.exception("Model switch failed")
            self.call_from_thread(
                self._on_worker_failed,
                f"Failed to load model {self.model_name}: {exc}",
            )
            return
        self.call_from_thread(self._on_model_loaded)
