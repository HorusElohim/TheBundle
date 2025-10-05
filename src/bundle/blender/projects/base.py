"""Abstract project definitions for Blender pipelines."""

from __future__ import annotations

from typing import Protocol, TypeVar

from bundle.core import data, tracer

ConfigT = TypeVar("ConfigT")


class ProjectMetadata(data.Data):
    """Describes a Blender project exposed through the CLI."""

    name: str
    description: str
    tags: tuple[str, ...] = ()


class Project(Protocol[ConfigT]):
    """Protocol all Blender projects should satisfy."""

    metadata: ProjectMetadata

    async def load_config(self, json_path: str | None = None) -> ConfigT:  # pragma: no cover - interface
        ...

    @tracer.Async.decorator.call_raise
    async def prepare(self, config: ConfigT) -> None:  # pragma: no cover - interface
        ...

    @tracer.Async.decorator.call_raise
    async def render(self, config: ConfigT) -> None:  # pragma: no cover - interface
        ...
