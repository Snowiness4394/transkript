import asyncio
import threading
import time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from textual.widgets import Button

from transkript.app import TranskriptApp
from transkript.transcriber import Segment, Transcriber


def fake_load(self):
    self._model = object()


def fake_transcribe(self, audio, language=None):
    return [Segment(0.0, 1.0, "hello")], SimpleNamespace(language="en")


def fast_record(duration, mic_device, loopback_device):
    time.sleep(0.01)
    return np.zeros(16000)


async def settle(app, pilot, seconds=0.3):
    for _ in range(int(seconds / 0.05)):
        await asyncio.sleep(0.05)
        await pilot.pause()


async def wait_for_state(app, pilot, state, timeout=4):
    for _ in range(int(timeout / 0.05)):
        if app.state == state:
            return
        await asyncio.sleep(0.05)
        await pilot.pause()
    raise AssertionError(f"expected state {state}, got {app.state}")


def common_patches(record_fn, mic_devices=None):
    return (
        patch.object(Transcriber, "load", fake_load),
        patch.object(Transcriber, "transcribe", fake_transcribe),
        patch("transkript.app.list_input_devices", return_value=mic_devices if mic_devices is not None else [{"index": 0, "name": "Mic", "channels": 1}]),
        patch("transkript.app.list_output_devices", return_value=[{"index": 1, "name": "Out", "channels": 2}]),
        patch("transkript.app.find_loopback_device", return_value=None),
        patch("transkript.app.record_mixed", record_fn),
    )


def test_buffer_limit_stops_recording_with_visible_reason(tmp_path):
    async def run():
        with ExitStack() as stack:
            stack.enter_context(patch("transkript.app.AUDIO_BUFFER_MAXLEN", 3))
            for p in common_patches(fast_record):
                stack.enter_context(p)
            app = TranskriptApp(output_dir=str(tmp_path))
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                app._start_recording()
                await wait_for_state(app, pilot, "done")

                assert app._recording_limit_reached is True
                assert "maximum" in app.status_text.lower()
                assert app.last_file
                assert "[00:00:00] hello" in Path(app.last_file).read_text(encoding="utf-8")

    asyncio.run(run())


def test_no_microphone_prevents_recording_with_clear_status():
    async def run():
        with ExitStack() as stack:
            for p in common_patches(fast_record, mic_devices=[]):
                stack.enter_context(p)
            app = TranskriptApp()
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                app._start_recording()
                await settle(app, pilot, 0.2)

                assert app.state == "idle"
                assert app._recording_thread is None
                assert "No microphone" in app.status_text
                assert app.query_one("#record-btn", Button).disabled is False

    asyncio.run(run())


def test_chunk_completed_after_stop_is_kept(tmp_path):
    entered = threading.Event()
    release = threading.Event()

    def blocking_record(duration, mic_device, loopback_device):
        entered.set()
        release.wait(0.5)
        return np.ones(16000, dtype=np.float32)

    async def run():
        with ExitStack() as stack:
            for p in common_patches(blocking_record):
                stack.enter_context(p)
            app = TranskriptApp(output_dir=str(tmp_path))
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                app._start_recording()
                for _ in range(40):
                    if entered.is_set():
                        break
                    await asyncio.sleep(0.05)
                    await pilot.pause()
                assert entered.is_set()

                app._stop_recording()
                release.set()
                await wait_for_state(app, pilot, "done")

                assert app.last_file
                assert "[00:00:00] hello" in Path(app.last_file).read_text(encoding="utf-8")

    asyncio.run(run())
