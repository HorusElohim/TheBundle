"""Scene lifetime management built on top of :class:`bundle.core.entity.Entity`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bundle.core import data
from bundle.core.entity import Entity

from .backend import USDBackend
from .model import SceneInfo


class USDScene(Entity):
    """Represents an opened USD scene and its lifecycle."""

    path: str
    revision: int = data.Field(default=0)
    backend: USDBackend = data.Field(default_factory=USDBackend, exclude=True)
    backend_stage: Any | None = data.Field(default=None, exclude=True)

    @classmethod
    def open(cls, path: str, backend: USDBackend | None = None) -> "USDScene":
        backend = backend or USDBackend()
        stage = backend.open(path)
        name = Path(path).stem or "scene"
        return cls(path=path, name=name, backend=backend, backend_stage=stage)

    def info(self) -> SceneInfo:
        if self.backend_stage is None:
            raise RuntimeError("USD scene is not initialized")
        return self.backend.stats(self.backend_stage)

    def close(self) -> None:
        self.backend_stage = None
