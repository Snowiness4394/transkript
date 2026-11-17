import asyncio
import sys
from unittest.mock import patch

from textual.widgets import Select, Switch

import transkript.__main__ as cli
from transkript.app import TranskriptApp
from transkript.transcriber import TranscribeSettings, Transcriber


def test_default_cli_run_uses_high_spec_settings():
    app = TranskriptApp()

    assert app.low_spec is False
    assert app.transcriber.settings == TranscribeSettings.high_spec()


def test_main_passes_low_spec_flag_to_app(monkeypatch):
    created = []

    class FakeApp:
        def __init__(self, **kwargs):
            created.append(kwargs)

        def run(self):
            pass

    monkeypatch.setattr(sys, "argv", ["transkript", "--low-spec"])
    with patch("transkript.app.TranskriptApp", FakeApp):
        cli.main()

    assert created == [
        {"model_name": "tiny", "output_dir": "./transcripts", "low_spec": True}
    ]


def test_low_spec_switch_starts_from_constructor_flag():
    async def run():
        with (
            patch.object(Transcriber, "load", lambda self: setattr(self, "_model", object())),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
        ):
            app = TranskriptApp(low_spec=False)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.query_one("#low-spec-switch", Switch).value is False

    asyncio.run(run())


def test_mount_keeps_cli_model_in_ui_and_transcriber():
    async def run():
        with (
            patch.object(Transcriber, "load", lambda self: setattr(self, "_model", object())),
            patch("transkript.app.list_input_devices", return_value=[]),
            patch("transkript.app.list_output_devices", return_value=[]),
            patch("transkript.app.find_loopback_device", return_value=None),
        ):
            app = TranskriptApp(model_name="small", low_spec=True)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.model_name == "small"
                assert app.transcriber.model_name == "small"
                assert app.query_one("#model-select", Select).value == "small"

    asyncio.run(run())
