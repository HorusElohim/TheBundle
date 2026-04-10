"""Bridge: gs3d → recon3d GaussiansOutput.

A synthesised cloud has no training checkpoint — the bridge creates a
sentinel ``GaussiansOutput`` whose ``checkpoint_path`` points to the PLY
itself.  Downstream stages that only care about ``ply_path`` (Blender,
USD, visualisation) work transparently.  Stages that assert the checkpoint
exists (e.g. Lambda runner) will surface a clear validation error rather
than silently misbehaving.
"""

from __future__ import annotations

from pathlib import Path

from bundle.core import logger
from bundle.recon3d.stages.gaussians.base import GaussiansOutput

from .data import GaussianCloud

log = logger.get_logger(__name__)


def to_gaussians_output(cloud: GaussianCloud) -> GaussiansOutput:
    """Wrap a :class:`GaussianCloud` as a :class:`GaussiansOutput`.

    The ``checkpoint_path`` is set to the PLY path itself (a harmless
    sentinel — it exists and satisfies path-presence checks).  The
    ``renders_dir`` is set to a ``renders/`` sibling of the PLY so that
    stages which write renders have a predictable location without
    requiring the caller to create it.
    """
    ply = cloud.path.resolve()
    output = GaussiansOutput(
        checkpoint_path=ply,
        ply_path=ply,
        renders_dir=ply.parent / "renders",
    )
    log.debug("bridge: GaussianCloud(%s) → GaussiansOutput(ply=%s)", ply.name, ply)
    return output
