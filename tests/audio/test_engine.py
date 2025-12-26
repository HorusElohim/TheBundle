from pathlib import Path

import numpy as np
import pytest

from bundle.audio.engine import apply_transforms, get_waveform, load_audio
from bundle.audio.models import AudioTransform


def _write_wav(path: Path, sample_rate: int, samples: np.ndarray) -> None:
    import wave

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.astype(np.int16).tobytes())


@pytest.fixture()
def tone_wav(tmp_path: Path) -> tuple[Path, int, float]:
    sample_rate = 8000
    duration_sec = 0.2
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    samples = (0.5 * np.sin(2 * np.pi * 440 * t) * (2**14)).astype(np.int16)
    path = tmp_path / "tone.wav"
    _write_wav(path, sample_rate, samples)
    return path, sample_rate, duration_sec


def test_load_audio_reads_metadata(tone_wav: tuple[Path, int, float]) -> None:
    path, sample_rate, duration_sec = tone_wav
    source = load_audio(path)

    assert source.sample_rate == sample_rate
    assert source.channels == 1
    assert source.duration_sec == pytest.approx(duration_sec, rel=1e-3)


def test_get_waveform_respects_pixels_and_zoom(tmp_path: Path) -> None:
    sample_rate = 4000
    total_duration = 1.0
    samples = np.arange(int(sample_rate * total_duration), dtype=np.int16)
    path = tmp_path / "ramp.wav"
    _write_wav(path, sample_rate, samples)

    source = load_audio(path)
    zoom = 2.0
    pixels = 120
    chunk = get_waveform(source, zoom=zoom, offset=0.0, pixels=pixels)

    assert len(chunk) == pixels
    assert chunk[0] == 0


def test_apply_transforms_gain_trim_fade() -> None:
    samples = np.ones(10, dtype=np.float32)
    transforms = [
        AudioTransform(type="gain", params={"db": 6}),
        AudioTransform(type="trim", params={"start": 2, "end": 8}),
        AudioTransform(type="fade", params={"direction": "out", "duration": 3}),
    ]

    processed = apply_transforms(samples, transforms)

    gain_factor = 10 ** (6 / 20)
    assert processed.shape[0] == 6
    assert processed[0] == pytest.approx(gain_factor)
    assert processed[2] == pytest.approx(0.0)
