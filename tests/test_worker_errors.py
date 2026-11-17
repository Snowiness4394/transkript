import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
from textual.widgets import Button, Select, Switch

from transkript.transcriber import Segment, TranscribeSettings, Transcriber
from transkript.app import TranskriptApp


async def settle(app, pilot, seconds=0.4):
    for _ in range(int(seconds / 0.05)):
        await asyncio.sleep(0.05)
        await pilot.pause()


def test_model_load_failure_restores_idle_and_reports_error():
    def boom(self):
        raise RuntimeError("offline")

    async def run():
        with (
            patch.object(Transcriber, "load", boom),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
        ):
            app = TranskriptApp()
            async with app.run_test() as pilot:
                await settle(app, pilot)
                assert app.state == "idle"
                assert "Failed to load model" in app.status_text
                assert app.query_one("#record-btn", Button).disabled is False
                assert app.query_one("#model-select", Select).disabled is False
                assert app.query_one("#low-spec-switch", Switch).disabled is False

    asyncio.run(run())


def test_model_switch_failure_reverts_model_and_restores_controls():
    calls = {"n": 0}

    def flaky_load(self):
        calls["n"] += 1
        if calls["n"] == 1:
            self._model = object()
        else:
            raise RuntimeError("download failed")

    async def run():
        with (
            patch.object(Transcriber, "load", flaky_load),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
        ):
            app = TranskriptApp()
            async with app.run_test() as pilot:
                await settle(app, pilot)
                app._load_new_model("small")
                await settle(app, pilot)
                assert app.state == "idle"
                assert "Failed to load model" in app.status_text
                assert app.model_name == "base"
                assert app.transcriber.model_name == "base"
                assert app.query_one("#model-select", Select).value == "base"
                assert app.query_one("#record-btn", Button).disabled is False

    asyncio.run(run())


def test_failed_low_spec_toggle_restores_mode_and_settings():
    calls = {"n": 0}

    def flaky_load(self):
        calls["n"] += 1
        if calls["n"] == 1:
            self._model = object()
        else:
            raise RuntimeError("offline")

    async def run():
        with (
            patch.object(Transcriber, "load", flaky_load),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
        ):
            app = TranskriptApp()
            async with app.run_test() as pilot:
                await settle(app, pilot)
                app.query_one("#low-spec-switch", Switch).value = True
                await settle(app, pilot)

                assert app.low_spec is False
                assert app.query_one("#low-spec-switch", Switch).value is False
                assert app.transcriber.settings == TranscribeSettings.high_spec()
                assert app.model_name == "base"
                assert app.transcriber.model_name == "base"
                assert "Failed to load model" in app.status_text

    asyncio.run(run())


def test_failed_transcription_resets_record_button_label():
    def fake_load(self):
        self._model = object()

    def fake_transcribe(self, audio, language=None):
        return [Segment(0.0, 1.0, "hello")], SimpleNamespace(language="en")

    async def run():
        with (
            patch.object(Transcriber, "load", fake_load),
            patch.object(Transcriber, "transcribe", fake_transcribe),
            patch.object(Transcriber, "save_transcript", side_effect=RuntimeError("disk full")),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
            patch("transkript.app.record_mixed", return_value=np.zeros(16000)),
        ):
            app = TranskriptApp()
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                app._start_recording()
                await settle(app, pilot, 0.2)
                app._stop_recording()
                await settle(app, pilot, 1.0)

                btn = app.query_one("#record-btn", Button)
                assert btn.disabled is False
                assert str(btn.label) == "Start Recording"
                assert btn.variant == "success"

    asyncio.run(run())


def test_save_failure_reports_error_instead_of_stuck_transcribing():
    def fake_load(self):
        self._model = object()

    def fake_transcribe(self, audio, language=None):
        return [Segment(0.0, 1.0, "hello")], SimpleNamespace(language="en")

    async def run():
        with (
            patch.object(Transcriber, "load", fake_load),
            patch.object(Transcriber, "transcribe", fake_transcribe),
            patch.object(
                Transcriber,
                "save_transcript",
                side_effect=RuntimeError("disk full"),
            ),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
            patch("transkript.app.record_mixed", return_value=np.zeros(16000)),
        ):
            app = TranskriptApp()
            async with app.run_test() as pilot:
                await settle(app, pilot, 0.2)
                app._start_recording()
                await settle(app, pilot, 0.2)
                app._stop_recording()
                await settle(app, pilot, 1.0)
                assert app.state == "idle"
                assert "Transcription failed" in app.status_text
                assert app.query_one("#record-btn", Button).disabled is False

    asyncio.run(run())
