import asyncio
import threading
from contextlib import ExitStack
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import numpy as np
from textual.widgets import Select

from transkript.app import TranskriptApp
from transkript.transcriber import Segment, Transcriber


def fake_load(self):
    self._model = object()


def blocking_transcribe(self, audio, language=None):
    release.wait(3)
    return [Segment(0.0, 1.0, "hello")], SimpleNamespace(language="en")


async def settle(app, pilot, seconds=0.4):
    for _ in range(int(seconds / 0.05)):
        await asyncio.sleep(0.05)
        await pilot.pause()


async def wait_for_state(app, pilot, state, timeout=3):
    for _ in range(int(timeout / 0.05)):
        if app.state == state:
            return
        await asyncio.sleep(0.05)
        await pilot.pause()
    raise AssertionError(f"expected state {state}, got {app.state}")


release = threading.Event()


def patch_common():
    return (
        patch.object(Transcriber, "load", fake_load),
        patch.object(Transcriber, "transcribe", blocking_transcribe),
        patch("transkript.app.list_input_devices", return_value=[]),
        patch("transkript.app.list_output_devices", return_value=[]),
        patch("transkript.app.find_loopback_device", return_value=None),
        patch("transkript.app.record_mixed", return_value=np.zeros(16000)),
    )


def test_model_select_is_disabled_while_recording_and_transcribing(tmp_path):
    async def run():
        with ExitStack() as stack:
            for p in patch_common():
                stack.enter_context(p)
            app = TranskriptApp(output_dir=str(tmp_path))
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                select = app.query_one("#model-select", Select)
                assert select.disabled is False

                app._start_recording()
                await settle(app, pilot, 0.1)
                assert select.disabled is True

                app._stop_recording()
                await wait_for_state(app, pilot, "transcribing")
                assert select.disabled is True

                release.set()
                await wait_for_state(app, pilot, "done")
                assert select.disabled is False

    release.clear()
    asyncio.run(run())


def test_model_change_during_transcription_is_rejected(tmp_path):
    async def run():
        with ExitStack() as stack:
            for p in patch_common():
                stack.enter_context(p)
            app = TranskriptApp(output_dir=str(tmp_path))
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                select = app.query_one("#model-select", Select)
                original = app.model_name

                app._start_recording()
                await settle(app, pilot, 0.1)
                app._stop_recording()
                await wait_for_state(app, pilot, "transcribing")

                app.on_model_changed(
                    cast(Any, SimpleNamespace(value="large-v3", select=select))
                )
                assert app.model_name == original
                assert select.value == original
                assert "Cannot change model" in app.status_text

                app._load_new_model("large-v3")
                assert app.model_name == original
                assert app.state == "transcribing"

                release.set()
                await wait_for_state(app, pilot, "done")
                assert app.last_file

    release.clear()
    asyncio.run(run())
