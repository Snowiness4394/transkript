"""Audio capture — device discovery, recording, mixing."""

from __future__ import annotations

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHANNELS = 1


def list_input_devices() -> list[dict]:
    """Return list of input (microphone) devices."""
    devices = sd.query_devices()
    result = []
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0 and "loopback" not in d["name"].lower():
            result.append({"index": i, "name": d["name"], "channels": d["max_input_channels"]})
    return result


def list_output_devices() -> list[dict]:
    """Return list of output devices that can be used for loopback capture."""
    devices = sd.query_devices()
    result = []
    seen = set()
    for i, d in enumerate(devices):
        if d["max_output_channels"] > 0:
            name = d["name"]
            if name not in seen:
                seen.add(name)
                result.append({"index": i, "name": name, "channels": d["max_output_channels"]})
    return result


def find_loopback_device(output_device_name: str | None = None) -> int | None:
    """Find the WASAPI loopback device for system audio capture.

    If output_device_name is given, look for a loopback with that name.
    Otherwise, find any loopback device automatically.
    """
    devices = sd.query_devices()

    # First try: find a loopback device explicitly
    if output_device_name:
        for i, d in enumerate(devices):
            if "loopback" in d["name"].lower() and output_device_name.lower() in d["name"].lower():
                return i

    # Second try: any loopback device
    for i, d in enumerate(devices):
        if "loopback" in d["name"].lower():
            return i

    # Third try: Stereo Mix (Windows fallback)
    for i, d in enumerate(devices):
        if "stereo mix" in d["name"].lower() and d["max_input_channels"] > 0:
            return i

    return None


def record_chunk(duration: float, device: int | None = None) -> np.ndarray:
    """Record a chunk of audio from the given device.

    Returns a flat float32 numpy array at SAMPLE_RATE.
    """
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=device,
    )
    sd.wait()
    return audio.flatten()


def record_mixed(duration: float, mic_device: int, loopback_device: int | None) -> np.ndarray:
    """Record from mic (and optionally loopback), mix them together.

    Returns a flat float32 numpy array at SAMPLE_RATE.
    """
    mic_audio = record_chunk(duration, device=mic_device)

    if loopback_device is not None:
        sys_audio = record_chunk(duration, device=loopback_device)
        # Mix: average the two signals
        audio = (mic_audio + sys_audio) / 2.0
    else:
        audio = mic_audio

    return audio
