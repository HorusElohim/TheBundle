"""Gaussians stage — renderer registry and factory."""

from __future__ import annotations

from .base import GaussiansStage
from .threedgrut import ThreeDGrutGaussians

_RENDERERS: dict[str, type[GaussiansStage]] = {
    "3dgut": ThreeDGrutGaussians,
    "3dgrt": ThreeDGrutGaussians,  # same tool, different Hydra config
}


def create_gaussians_stage(
    renderer: str = "3dgut",
    **kwargs,
) -> GaussiansStage:
    """Create a Gaussians stage for the given renderer."""
    cls = _RENDERERS.get(renderer)
    if cls is None:
        raise NotImplementedError(f"Gaussian renderer '{renderer}' not yet implemented")
    return cls(renderer=renderer, **kwargs)


__all__ = ["GaussiansStage", "ThreeDGrutGaussians", "create_gaussians_stage"]
