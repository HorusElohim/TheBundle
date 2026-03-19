"""SfM stage — backend registry and factory."""

from __future__ import annotations

from .base import SfmBackend, SfmStage
from .colmap import ColmapSfm

_BACKENDS: dict[SfmBackend, type[SfmStage]] = {
    SfmBackend.COLMAP: ColmapSfm,
}


def create_sfm_stage(
    backend: SfmBackend = SfmBackend.COLMAP,
    **kwargs,
) -> SfmStage:
    """Create an SfM stage for the given backend."""
    cls = _BACKENDS.get(backend)
    if cls is None:
        raise NotImplementedError(f"SfM backend '{backend.value}' not yet implemented")
    return cls(backend=backend, **kwargs)


__all__ = ["ColmapSfm", "SfmStage", "create_sfm_stage"]
