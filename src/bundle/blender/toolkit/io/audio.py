"""Audio utilities for Blender scripts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from bundle.core import logger, tracer

try:  # pragma: no cover - Blender-only dependency
    import aud  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    aud = None  # type: ignore

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import Scene
    from numpy.typing import NDArray

log = logger.get_logger(__name__)


def _require_aud() -> None:
    if aud is None:  # pragma: no cover - executed outside Blender Python
        raise RuntimeError("aud is not available; ensure this runs inside Blender")


def _require_bpy() -> None:
    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")


@tracer.Sync.decorator.call_raise
def sample_audio_envelope(
    audio_path: Path,
    *,
    fps: int,
    frame_count: int | None,
    normalize: float | None = None,
    smooth_window: int = 0,
) -> tuple[NDArray[np.float32], int, int]:
    """Return an RMS envelope sampled from the audio clip."""

    _require_aud()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    sound = aud.Sound.file(str(audio_path))
    rate, channels = sound.specs
    samples = np.asarray(sound.data(), dtype=np.float32).ravel()

    if channels <= 0 or rate <= 0:
        raise RuntimeError("Invalid audio stream")

    total_seconds = samples.size / (rate * channels)
    if total_seconds <= 0:
        raise RuntimeError("Audio clip contains no samples")

    total_frames = int(total_seconds * fps)
    target_frames = frame_count if frame_count and frame_count > 0 else total_frames
    samples_per_frame = max(int(rate / fps), 1)

    envelope = np.zeros(target_frames, dtype=np.float32)
    for frame_idx in range(target_frames):
        start = frame_idx * samples_per_frame * channels
        end = start + samples_per_frame * channels
        window = samples[start:end]
        if window.size == 0:
            continue
        if channels > 1:
            cut = (window.size // channels) * channels
            window = window[:cut].reshape(-1, channels).mean(axis=1)
        rms = float(np.sqrt(np.mean(np.square(window)))) if window.size else 0.0
        envelope[frame_idx] = rms

    if smooth_window and smooth_window > 1:
        kernel = np.ones(smooth_window, dtype=np.float32) / float(smooth_window)
        envelope = np.convolve(envelope, kernel, mode="same").astype(np.float32)

    if normalize and normalize > 0:
        peak = float(envelope.max())
        if peak > 0:
            envelope *= normalize / peak

    log.info(
        "Audio envelope sampled: frames=%s, rate=%s, channels=%s",
        envelope.size,
        rate,
        channels,
    )
    return envelope, rate, channels


@tracer.Sync.decorator.call_raise
def add_sound_strip(audio_path: Path, *, scene: Scene | None = None) -> None:
    """Ensure the audio clip is available in the current VSE."""

    _require_bpy()
    scene = scene or bpy.context.scene
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    editor = scene.sequence_editor
    for strip in list(editor.sequences_all):
        if strip.type == "SOUND":
            editor.sequences.remove(strip)

    editor.sequences.new_sound(
        name="Audio",
        filepath=str(audio_path),
        channel=1,
        frame_start=scene.frame_start,
    )

    scene.sync_mode = "AUDIO_SYNC"
    scene.use_audio_scrub = True
    scene.use_audio = True
    log.info("Audio strip added to VSE: %s", audio_path)