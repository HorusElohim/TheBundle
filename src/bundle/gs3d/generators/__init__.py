"""Synthetic Gaussian splat generators — backend registry and factory."""

from __future__ import annotations

from .base import Generator
from .mesh import MeshToGaussiansGenerator
from .primitives import (
    CubeGenerator,
    RandomCloudGenerator,
    SphereGenerator,
    TorusGenerator,
)

_GENERATORS: dict[str, type[Generator]] = {
    "sphere": SphereGenerator,
    "cube": CubeGenerator,
    "torus": TorusGenerator,
    "cloud": RandomCloudGenerator,
    "mesh": MeshToGaussiansGenerator,
}


def create_generator(shape: str, **kwargs) -> Generator:
    """Instantiate a generator for the named shape."""
    cls = _GENERATORS.get(shape)
    if cls is None:
        raise NotImplementedError(f"Gaussian generator '{shape}' not registered. Known: {sorted(_GENERATORS)}")
    return cls(**kwargs)


def available_shapes() -> list[str]:
    """Return the list of registered shape names."""
    return sorted(_GENERATORS)


__all__ = [
    "CubeGenerator",
    "Generator",
    "MeshToGaussiansGenerator",
    "RandomCloudGenerator",
    "SphereGenerator",
    "TorusGenerator",
    "available_shapes",
    "create_generator",
]
