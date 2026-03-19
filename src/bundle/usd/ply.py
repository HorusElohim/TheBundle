"""PLY file reading and validation.

Provides utilities for loading PLY point cloud files (e.g. Gaussian splat exports)
and validating their structure before USD conversion.
"""

from __future__ import annotations

from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data

log = logger.get_logger(__name__)


class PlyInfo(Data):
    """Metadata about a PLY file."""

    path: Path
    vertex_count: int = 0
    has_colors: bool = False
    has_normals: bool = False


async def read_ply_info(path: Path) -> PlyInfo:
    """Read PLY header and return metadata without loading full vertex data.

    Implementation pending — will parse the PLY ASCII/binary header to extract
    vertex count and available properties.
    """
    if not path.exists():
        raise FileNotFoundError(f"PLY file not found: {path}")

    raise NotImplementedError("PLY reader implementation pending")
