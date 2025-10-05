"""Simple registry to expose Blender projects through the CLI."""

from __future__ import annotations

from collections.abc import Iterable

from bundle.core import logger

from .base import Project

log = logger.get_logger(__name__)

_REGISTRY: dict[str, Project] = {}


def register(name: str, project: Project) -> None:
    if name in _REGISTRY:
        raise ValueError(f"Project {name!r} already registered")
    _REGISTRY[name] = project
    log.debug("Registered Blender project: %s", name)


def get(name: str) -> Project:
    return _REGISTRY[name]


def items() -> Iterable[tuple[str, Project]]:
    return _REGISTRY.items()
