from unittest.mock import patch

import numpy as np

from transkript import audio


def test_record_mixed_starts_loopback_before_waiting():
    events = []
    frames_seen = []

    def fake_rec(frames, *, samplerate, channels, dtype, device):
        frames_seen.append(frames)
        events.append(("rec", device))
        value = 1.0 if device == 0 else 3.0
        return np.full(frames, value, dtype=np.float32)

    def fake_wait():
        events.append(("wait", None))

    with (
        patch.object(audio.sd, "rec", fake_rec),
        patch.object(audio.sd, "wait", fake_wait),
    ):
        result = audio.record_mixed(0.1, 0, 1)

    assert events == [("rec", 0), ("rec", 1), ("wait", None)]
    assert len(result) == frames_seen[0]
    assert np.allclose(result, 2.0)


def test_record_mixed_int16_starts_loopback_before_waiting():
    events = []

    def fake_rec(frames, *, samplerate, channels, dtype, device):
        events.append(("rec", device))
        value = 1000 if device == 0 else 3000
        return np.full(frames, value, dtype=np.int16)

    def fake_wait():
        events.append(("wait", None))

    with (
        patch.object(audio.sd, "rec", fake_rec),
        patch.object(audio.sd, "wait", fake_wait),
    ):
        result = audio.record_mixed_int16(0.1, 0, 1)

    assert events == [("rec", 0), ("rec", 1), ("wait", None)]
    assert np.all(result == 2000)


def test_record_mixed_logs_when_loopback_fails(caplog):
    waits = []

    def fake_rec(frames, *, samplerate, channels, dtype, device):
        if device == 1:
            raise RuntimeError("device busy")
        return np.full(frames, 2.0, dtype=np.float32)

    def fake_wait():
        waits.append(True)

    with (
        patch.object(audio.sd, "rec", fake_rec),
        patch.object(audio.sd, "wait", fake_wait),
    ):
        result = audio.record_mixed(0.01, 0, 1)

    assert np.allclose(result, 2.0)
    assert len(waits) == 1
    assert "Loopback capture failed" in caplog.text
