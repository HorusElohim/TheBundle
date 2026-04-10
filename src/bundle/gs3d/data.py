"""Core data contracts for synthetic Gaussian splat clouds.

These are pure metadata models — no numpy arrays.  Heavy numeric data lives
in PLY files on disk; the models in this module hold the path plus a small
amount of summary information that downstream stages can read without loading
the full point cloud.

The in-memory numeric representation lives in :class:`bundle.gs3d.ply.GaussianCloudArrays`,
which is intentionally *not* a :class:`Data` subclass because it owns numpy
buffers that should never round-trip through JSON.
"""

from __future__ import annotations

from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data, Field

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# Static cloud (3D)
# ---------------------------------------------------------------------------


class GaussianCloud(Data):
    """Metadata for a single Gaussian splat point cloud stored on disk.

    Attributes:
        path: Location of the backing 3DGS-format PLY file.
        num_gaussians: Number of Gaussians in the cloud.
        sh_degree: Spherical harmonics degree (0..3).  Degree N has
            ``(N+1)**2`` coefficients per RGB channel; for the standard
            3DGS PLY layout that means 3 DC coefficients (``f_dc_0..2``)
            and ``3 * ((N+1)**2 - 1)`` rest coefficients (``f_rest_*``).
        bbox_min: Axis-aligned bounding box minimum corner.
        bbox_max: Axis-aligned bounding box maximum corner.
    """

    path: Path
    num_gaussians: int = 0
    sh_degree: int = 3
    bbox_min: tuple[float, float, float] = (0.0, 0.0, 0.0)
    bbox_max: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def validate_exists(self) -> bool:
        if not self.path.exists():
            log.warning("GaussianCloud missing: %s", self.path)
            return False
        return True


# ---------------------------------------------------------------------------
# Temporal sequence (4D)
# ---------------------------------------------------------------------------


class GaussianSequence(Data):
    """Ordered sequence of Gaussian clouds representing a 4D animation.

    A sequence is the simplest 4D representation: one PLY frame per keyframe,
    with downstream tools handling interpolation.  The temporal generators in
    :mod:`bundle.gs3d.temporal` populate this structure.

    Attributes:
        frames_dir: Directory containing per-frame PLY files.
        frame_count: Number of frames in the sequence.
        fps: Playback rate, used by exporters and players.
        frame_paths: Ordered list of PLY paths (frame 0 first).
    """

    frames_dir: Path
    frame_count: int = 0
    fps: float = 30.0
    frame_paths: list[Path] = Field(default_factory=list)

    def validate_exists(self) -> bool:
        if not self.frames_dir.is_dir():
            log.warning("GaussianSequence frames_dir missing: %s", self.frames_dir)
            return False
        missing = [p for p in self.frame_paths if not p.exists()]
        if missing:
            log.warning("GaussianSequence missing %d frame(s)", len(missing))
            return False
        return True
