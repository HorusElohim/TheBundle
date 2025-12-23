from __future__ import annotations

import aifc
import hashlib
import wave
from pathlib import Path
from typing import Iterable

import numpy as np

from bundle.core import logger

from .models import AudioSource, AudioTransform

TARGET_PIXELS = 2048


class UnsupportedAudioFormatError(RuntimeError):
    pass


class AudioDecodingError(RuntimeError):
    pass


SUPPORTED_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff"}
log = logger.get_logger(__name__)


def _open_reader(path: Path):
    suffix = path.suffix.lower()
    if suffix in {".aif", ".aiff"}:
        return aifc.open(str(path), "rb")
    if suffix in {".wav", ".wave"}:
        return wave.open(str(path), "rb")
    raise UnsupportedAudioFormatError(f"Unsupported audio format: {suffix}")


def load_audio(path: str | Path) -> AudioSource:
    audio_path = Path(path)
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    if audio_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedAudioFormatError(f"Unsupported audio format: {audio_path.suffix}")

    with _open_reader(audio_path) as reader:
        sample_rate = reader.getframerate()
        channels = reader.getnchannels()
        frames = reader.getnframes()
        duration_sec = frames / float(sample_rate) if sample_rate else 0.0

    log.info(
        "Loaded audio: path=%s sample_rate=%s channels=%s frames=%s duration=%.3fs",
        audio_path,
        sample_rate,
        channels,
        frames,
        duration_sec,
    )

    source_id = hashlib.sha256(str(audio_path).encode("utf-8")).hexdigest()
    return AudioSource(
        id=source_id,
        path=str(audio_path),
        sample_rate=sample_rate,
        channels=channels,
        duration_sec=duration_sec,
    )


def _read_samples(path: Path, start_frame: int, frame_count: int) -> np.ndarray:
    with _open_reader(path) as reader:
        reader.setpos(max(0, start_frame))
        raw = reader.readframes(frame_count)
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()

    if sample_width == 1:
        dtype = np.int8
    elif sample_width == 2:
        dtype = np.int16
    elif sample_width == 4:
        dtype = np.int32
    else:
        raise AudioDecodingError(f"Unsupported sample width: {sample_width}")

    data = np.frombuffer(raw, dtype=dtype)
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    log.debug(
        "Read samples: path=%s start_frame=%s frame_count=%s channels=%s sample_width=%s",
        path,
        start_frame,
        frame_count,
        channels,
        sample_width,
    )
    return data.astype(np.float32)


def get_waveform(source: AudioSource, zoom: float, offset: float, pixels: int = TARGET_PIXELS) -> np.ndarray:
    audio_path = Path(source.path)
    start_frame = max(0, int(offset * source.sample_rate))
    frame_count = max(1, int(max(1.0, zoom) * max(1, pixels)))

    samples = _read_samples(audio_path, start_frame, frame_count)
    downsample_step = max(1, int(zoom))
    if downsample_step > 1:
        samples = samples[::downsample_step]
    log.debug(
        "Waveform slice: start_frame=%s frame_count=%s zoom=%s pixels=%s downsample=%s samples=%s",
        start_frame,
        frame_count,
        zoom,
        pixels,
        downsample_step,
        len(samples),
    )
    return samples


def apply_transforms(samples: np.ndarray, transforms: Iterable[AudioTransform]) -> np.ndarray:
    output = samples.astype(np.float32, copy=True)
    for transform in transforms:
        if transform.type == "gain":
            params = transform.params or {}
            if "db" in params:
                factor = 10 ** (float(params.get("db", 0.0)) / 20.0)
            else:
                factor = float(params.get("factor", 1.0))
            output *= factor
        elif transform.type == "trim":
            params = transform.params or {}
            start = params.get("start", 0)
            end = params.get("end", len(output))
            if isinstance(start, float) and 0 < start < 1:
                start = int(start * len(output))
            if isinstance(end, float) and 0 < end <= 1:
                end = int(end * len(output))
            output = output[int(start) : int(end)]
        elif transform.type == "fade":
            params = transform.params or {}
            direction = params.get("direction", "in")
            duration = int(params.get("duration", len(output) // 10))
            duration = max(1, min(duration, len(output)))
            envelope = np.linspace(0.0, 1.0, num=duration, dtype=np.float32)
            if direction == "out":
                envelope = envelope[::-1]
            faded = output.copy()
            faded[:duration] *= envelope
            output = faded
    return output
