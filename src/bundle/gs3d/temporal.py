"""4D Gaussian sequence generation via keyframed rigid motions.

A :class:`TemporalGenerator` reads a static PLY, applies a per-frame
rigid transform derived from a :class:`MotionConfig`, and writes one
output PLY per frame into ``output_dir``.

Supported motions
-----------------
rigid       -- no motion (identity); useful as a baseline / loop test
oscillate   -- sinusoidal translation along one axis
explode     -- positions scale outward from the origin over time
orbit       -- rotation about a fixed axis (e.g. a 360° turntable)

The output contract is :class:`bundle.gs3d.data.GaussianSequence`; the
on-disk layout is ``<output_dir>/<frame_index:04d>.ply``.

All transforms operate on positions only.  Rotations (quaternions) and
scales are copied unchanged — downstream stages (Blender, USD) that need
animated orientations can extend :class:`MotionConfig` with additional
fields.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Literal

from bundle.core import logger
from bundle.core.entity import Entity

from .data import GaussianCloud, GaussianSequence
from .ply import GaussianCloudArrays, read_ply, write_ply

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# Motion configuration
# ---------------------------------------------------------------------------


class MotionConfig(Entity):
    """Parameters describing a single 4D motion.

    Attributes:
        motion_type: One of ``rigid``, ``oscillate``, ``explode``, ``orbit``.
        amplitude:   Scale of the motion (metres for translation, radians for orbit).
        frequency:   Cycles per second; combined with ``frame_count`` and ``fps``
                     to compute the per-frame angle/displacement.
        axis:        Primary axis letter (``x``, ``y``, or ``z``).
    """

    name: str = "motion"
    motion_type: Literal["rigid", "oscillate", "explode", "orbit"] = "orbit"
    amplitude: float = 1.0
    frequency: float = 1.0
    axis: Literal["x", "y", "z"] = "y"

    @property
    def axis_index(self) -> int:
        return {"x": 0, "y": 1, "z": 2}[self.axis]


# ---------------------------------------------------------------------------
# Per-frame transforms
# ---------------------------------------------------------------------------


def _apply_rigid(positions, _t: float, _cfg: MotionConfig):
    return positions


def _apply_oscillate(positions, t: float, cfg: MotionConfig):
    import numpy as np

    offset = np.zeros(3, dtype=np.float32)
    offset[cfg.axis_index] = cfg.amplitude * math.sin(2.0 * math.pi * cfg.frequency * t)
    return positions + offset


def _apply_explode(positions, t: float, cfg: MotionConfig):
    scale = 1.0 + cfg.amplitude * t
    return positions * scale


def _apply_orbit(positions, t: float, cfg: MotionConfig):
    """Rotate positions about ``cfg.axis`` by ``amplitude * 2π * frequency * t``."""
    import numpy as np

    angle = cfg.amplitude * 2.0 * math.pi * cfg.frequency * t
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    ax = cfg.axis_index
    # The two axes that rotate (the ones perpendicular to the orbit axis).
    a0, a1 = [i for i in range(3) if i != ax]
    result = positions.copy()
    result[:, a0] = cos_a * positions[:, a0] - sin_a * positions[:, a1]
    result[:, a1] = sin_a * positions[:, a0] + cos_a * positions[:, a1]
    return result


_TRANSFORMS = {
    "rigid": _apply_rigid,
    "oscillate": _apply_oscillate,
    "explode": _apply_explode,
    "orbit": _apply_orbit,
}


# ---------------------------------------------------------------------------
# Temporal generator
# ---------------------------------------------------------------------------


class TemporalGenerator(Entity):
    """Apply a :class:`MotionConfig` to a static PLY and emit a frame sequence.

    Attributes:
        ply_path:    Source static Gaussian cloud.
        motion:      Motion configuration.
        frame_count: Number of output frames.
        fps:         Playback rate (written into :class:`GaussianSequence` metadata).
        output_dir:  Directory to write per-frame PLY files.
    """

    name: str = "temporal"
    ply_path: Path
    motion: MotionConfig
    frame_count: int = 30
    fps: float = 30.0
    output_dir: Path

    async def generate(self) -> GaussianSequence:
        import numpy as np

        source: GaussianCloudArrays = await read_ply(self.ply_path)
        transform = _TRANSFORMS[self.motion.motion_type]
        duration = self.frame_count / self.fps
        frame_paths: list[Path] = []
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for idx in range(self.frame_count):
            t = (idx / max(self.frame_count - 1, 1)) * duration

            frame = GaussianCloudArrays(data=source.data.copy(), sh_degree=source.sh_degree)
            positions = np.stack([frame.data["x"], frame.data["y"], frame.data["z"]], axis=-1).astype(np.float32)
            new_pos = transform(positions, t, self.motion).astype(np.float32)
            frame.data["x"] = new_pos[:, 0]
            frame.data["y"] = new_pos[:, 1]
            frame.data["z"] = new_pos[:, 2]

            out_path = self.output_dir / f"{idx:04d}.ply"
            await write_ply(out_path, frame)
            frame_paths.append(out_path)

        log.info(
            "TemporalGenerator: %d frames, motion=%s, axis=%s → %s",
            self.frame_count,
            self.motion.motion_type,
            self.motion.axis,
            self.output_dir,
        )
        return GaussianSequence(
            frames_dir=self.output_dir,
            frame_count=self.frame_count,
            fps=self.fps,
            frame_paths=frame_paths,
        )
