"""Visualization stage — backend registry and factory."""

from __future__ import annotations

from .base import VisualizationStage
from .opensplat import OpenSplatVisualization

_BACKENDS: dict[str, type[VisualizationStage]] = {
    "opensplat": OpenSplatVisualization,
}


def create_visualization_stage(
    backend: str = "opensplat",
    **kwargs,
) -> VisualizationStage:
    """Create a VisualizationStage for the given backend."""
    cls = _BACKENDS.get(backend)
    if cls is None:
        raise NotImplementedError(f"Visualization backend '{backend}' not implemented")
    return cls(backend=backend, **kwargs)


__all__ = ["OpenSplatVisualization", "VisualizationStage", "create_visualization_stage"]
