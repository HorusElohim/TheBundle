"""gs3d — synthetic 3D / 4D Gaussian splatting generation.

Sibling module to ``bundle.recon3d``.  Where recon3d *reconstructs* Gaussian
splats from images (SfM → training → PLY), gs3d *synthesises* them from
geometric definitions: procedural primitives, mesh sampling, or Blender
authored geometry.

Both modules converge on the same on-disk PLY format, so downstream stages
(Blender import, USD export, OpenSplat preview) work transparently for either
origin via :mod:`bundle.gs3d.bridge`.
"""

from bundle.core import logger

log = logger.get_logger(__name__)
log.setLevel(logger.Level.DEBUG)
