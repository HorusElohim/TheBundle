"""Base configuration models shared by Blender projects."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from bundle.core import data, logger

log = logger.get_logger(__name__)


class BlenderPaths(data.Data):
    """Paths required by host-side orchestration."""

    blender_executable: Optional[Path] = None
    python_executable: Optional[Path] = None
    scripts_dir: Optional[Path] = None


class RenderSettings(data.Data):
    """Rendering knobs shared across projects."""

    engine: str = "CYCLES"
    resolution_x: int = 1920
    resolution_y: int = 1080
    frame_start: int = 1
    frame_end: int = 250
    output_path: Path | None = None
