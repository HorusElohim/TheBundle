"""Gaussians stage — CUDA training backend registry and factory."""

from __future__ import annotations

from bundle.core.platform import platform_info

from .base import GaussiansStage
from .threedgrut import ThreeDGrutGaussians

_RENDERERS: dict[str, type[GaussiansStage]] = {
    "3dgut": ThreeDGrutGaussians,
    "3dgrt": ThreeDGrutGaussians,  # same tool, different Hydra config
}


def _resolve_auto_renderer() -> str:
    """Pick the best CUDA renderer for the current platform.

    Raises RuntimeError on non-CUDA platforms — training requires CUDA.
    Use 'bundle recon3d visualize' (OpenSplat) for local Metal/CPU preview.
    """
    if not platform_info.has_cuda:
        raise RuntimeError(
            "No CUDA detected. Gaussian training requires CUDA. "
            "Run on a CUDA machine or use --lambda to train on Lambda Labs. "
            "For a local preview use: bundle recon3d visualize"
        )
    return "3dgut"


def create_gaussians_stage(
    renderer: str = "3dgut",
    **kwargs,
) -> GaussiansStage:
    """Create a CUDA Gaussians training stage for the given renderer."""
    if renderer == "auto":
        renderer = _resolve_auto_renderer()
    cls = _RENDERERS.get(renderer)
    if cls is None:
        raise NotImplementedError(f"Gaussian renderer '{renderer}' not yet implemented")
    return cls(renderer=renderer, **kwargs)


__all__ = ["GaussiansStage", "ThreeDGrutGaussians", "create_gaussians_stage"]
