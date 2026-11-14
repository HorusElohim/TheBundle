"""PLY file reading and validation.

Provides utilities for loading PLY point cloud files (e.g. Gaussian splat
exports) and validating their structure before USD conversion.

Implementation delegates to ``bundle.gs3d.ply.read_ply_header`` — a
header-only parse that avoids loading the vertex payload.
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
    """Read PLY header and return metadata without loading the vertex payload.

    Delegates to :func:`bundle.gs3d.ply.read_ply_header` which parses the
    standard 3DGS binary PLY header.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        ValueError: if the file is not a valid PLY.
    """
    from bundle.gs3d.ply import property_names, read_ply_header

    cloud = await read_ply_header(path)
    props = property_names(cloud.sh_degree)
    return PlyInfo(
        path=cloud.path,
        vertex_count=cloud.num_gaussians,
        has_colors="f_dc_0" in props,
        has_normals="nx" in props,
    )
