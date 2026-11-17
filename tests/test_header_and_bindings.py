import asyncio
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from textual.binding import Binding

from transkript.app import TranskriptApp
from transkript.transcriber import Segment, Transcriber


def test_transcript_header_distinguishes_auto_selected_and_unknown_language(tmp_path):
    transcriber = Transcriber()
    segments = [Segment(0.0, 1.0, "hello")]

    auto = tmp_path / "auto.txt"
    explicit = tmp_path / "explicit.txt"
    unknown = tmp_path / "unknown.txt"

    transcriber.save_transcript(segments, auto, 1.0, language="en")
    transcriber.save_transcript(
        segments, explicit, 1.0, language="en", language_was_explicit=True
    )
    transcriber.save_transcript(segments, unknown, 1.0, language="unknown")

    auto_text = Path(auto).read_text(encoding="utf-8")
    explicit_text = Path(explicit).read_text(encoding="utf-8")
    unknown_text = Path(unknown).read_text(encoding="utf-8")

    assert "Language: en (auto-detected)" in auto_text
    assert "Language: en (selected)" in explicit_text
    assert "Language: unknown" in unknown_text
    assert "(auto-detected)" not in unknown_text


def test_app_exposes_start_stop_and_quit_bindings():
    bindings = TranskriptApp.BINDINGS
    assert any(
        isinstance(b, Binding) and b.key == "enter" and b.action == "toggle_recording"
        for b in bindings
    )
    assert any(isinstance(b, Binding) and b.key == "q" for b in bindings)


def test_toggle_recording_action_starts_and_stops(tmp_path):
    def fake_load(self):
        self._model = object()

    def fake_record(duration, mic_device, loopback_device):
        return np.zeros(16000)

    def fake_transcribe(self, audio, language=None):
        return [Segment(0.0, 1.0, "hello")], SimpleNamespace(language="en")

    async def run():
        with ExitStack() as stack:
            stack.enter_context(patch.object(Transcriber, "load", fake_load))
            stack.enter_context(patch.object(Transcriber, "transcribe", fake_transcribe))
            stack.enter_context(patch("transkript.app.list_input_devices", return_value=[{"index": 0, "name": "Mic", "channels": 1}]))
            stack.enter_context(patch("transkript.app.list_output_devices", return_value=[]))
            stack.enter_context(patch("transkript.app.find_loopback_device", return_value=None))
            stack.enter_context(patch("transkript.app.record_mixed", fake_record))
            app = TranskriptApp(output_dir=str(tmp_path))
            async with app.run_test() as pilot:
                for _ in range(10):
                    await asyncio.sleep(0.05)
                    await pilot.pause()

                app.action_toggle_recording()
                assert app.state == "recording"

                app.action_toggle_recording()
                for _ in range(60):
                    if app.state == "done":
                        break
                    await asyncio.sleep(0.05)
                    await pilot.pause()
                assert app.state == "done"
                assert app.last_file

    asyncio.run(run())
