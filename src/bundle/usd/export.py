"""USDZ scene building and export.

Converts point cloud data (PLY) into USD scenes.  Two code paths:

1. **3DGRUT delegate** — when running inside the 3DGRUT pod, delegate to
   ``threedgrut.export.scripts.ply_to_usd`` which handles Gaussian-specific
   attributes (opacity, spherical harmonics, etc.).

2. **Standalone** — when ``pxr`` (OpenUSD Python bindings) is available,
   build a minimal USD scene directly.  This path is for local use or
   environments without 3DGRUT installed.
"""

from __future__ import annotations

from pathlib import Path

from bundle.core import logger

log = logger.get_logger(__name__)


async def ply_to_usdz(ply_path: Path, output_path: Path) -> Path:
    """Convert a PLY point cloud to a USDZ file.

    Args:
        ply_path: Path to the source PLY file.
        output_path: Desired path for the output USDZ file.

    Returns:
        The resolved output path on success.
    """
    if not ply_path.exists():
        raise FileNotFoundError(f"PLY file not found: {ply_path}")

    # Try 3DGRUT's exporter first (available inside the gaussians pod)
    try:
        from threedgrut.export.scripts import ply_to_usd  # type: ignore[import-untyped]

        log.info("Using 3DGRUT exporter: %s -> %s", ply_path, output_path)
        ply_to_usd.main(str(ply_path), str(output_path))
        return output_path.resolve()
    except ImportError:
        pass

    # Fallback: standalone via OpenUSD Python bindings
    try:
        from pxr import Usd, UsdGeom  # type: ignore[import-untyped]

        log.info("Using pxr (OpenUSD) exporter: %s -> %s", ply_path, output_path)
        raise NotImplementedError("Standalone pxr export implementation pending")
    except ImportError:
        raise RuntimeError(
            "No USD export backend available. Install 'usd-core' (pip install thebundle[usd]) or run inside the 3DGRUT pod."
        ) from ImportError
