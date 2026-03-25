"""Gaussians stage — renderer registry and factory."""

from __future__ import annotations

from bundle.core.platform import platform_info

from .base import GaussiansStage
from .opensplat import OpenSplatGaussians
from .threedgrut import ThreeDGrutGaussians

_RENDERERS: dict[str, type[GaussiansStage]] = {
    "3dgut": ThreeDGrutGaussians,
    "3dgrt": ThreeDGrutGaussians,  # same tool, different Hydra config
    "opensplat": OpenSplatGaussians,
}


def _resolve_auto_renderer() -> str:
    """Pick the best available renderer for the current platform."""
    if platform_info.has_cuda:
        return "3dgut"
    return "opensplat"


def create_gaussians_stage(
    renderer: str = "3dgut",
    **kwargs,
) -> GaussiansStage:
    """Create a Gaussians stage for the given renderer."""
    if renderer == "auto":
        renderer = _resolve_auto_renderer()
    cls = _RENDERERS.get(renderer)
    if cls is None:
        raise NotImplementedError(f"Gaussian renderer '{renderer}' not yet implemented")
    return cls(renderer=renderer, **kwargs)


__all__ = ["GaussiansStage", "OpenSplatGaussians", "ThreeDGrutGaussians", "create_gaussians_stage"]
