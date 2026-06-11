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
    """Find the WASAPI loopback device for system audio capture."""
    devices = sd.query_devices()

    if output_device_name:
        for i, d in enumerate(devices):
            if "loopback" in d["name"].lower() and output_device_name.lower() in d["name"].lower():
                return i

    for i, d in enumerate(devices):
        if "loopback" in d["name"].lower():
            return i

    for i, d in enumerate(devices):
        if "stereo mix" in d["name"].lower() and d["max_input_channels"] > 0:
            return i

    return None


def record_chunk(duration: float, device: int | None = None) -> np.ndarray:
    """Record a chunk of audio from the given device. Returns flat float32."""
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        device=device,
    )
    sd.wait()
    return audio.flatten()


def record_chunk_int16(duration: float, device: int | None = None) -> np.ndarray:
    """Record a chunk of audio and return as int16."""
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        device=device,
    )
    sd.wait()
    return audio.flatten()


def int16_to_float32(audio_int16: np.ndarray) -> np.ndarray:
    """Convert int16 audio to float32 for Whisper."""
    return audio_int16.astype(np.float32) / 32768.0


def record_mixed(duration: float, mic_device: int, loopback_device: int | None) -> np.ndarray:
    """Record from mic (and optionally loopback), mix them together. Returns float32."""
    mic_audio = record_chunk(duration, device=mic_device)

    if loopback_device is not None:
        try:
            sys_audio = record_chunk(duration, device=loopback_device)
            audio = (mic_audio + sys_audio) / 2.0
        except Exception:
            audio = mic_audio
    else:
        audio = mic_audio

    return audio


def record_mixed_int16(duration: float, mic_device: int, loopback_device: int | None) -> np.ndarray:
    """Record from mic (and optionally loopback) as int16, mix, return int16."""
    mic_audio = record_chunk_int16(duration, device=mic_device)

    if loopback_device is not None:
        try:
            sys_audio = record_chunk_int16(duration, device=loopback_device)
            mixed = (mic_audio.astype(np.int32) + sys_audio.astype(np.int32)) // 2
            return mixed.astype(np.int16)
        except Exception:
            return mic_audio
    else:
        return mic_audio
