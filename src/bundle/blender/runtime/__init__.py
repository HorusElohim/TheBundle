"""Blender runtime package."""

from __future__ import annotations

from pathlib import Path

from bundle.core import tracer

from .app import BlenderEnvironment, BlenderRuntime, runtime as _runtime


def runtime() -> BlenderRuntime:
    return _runtime()


@tracer.Async.decorator.call_raise
async def discover_default_environment() -> BlenderEnvironment:
    return await runtime().discover_default()


def resolve_environment_from_python(python_path: Path) -> BlenderEnvironment | None:
    return runtime().from_python(python_path)


def resolve_environment_from_install(install_root: Path) -> BlenderEnvironment | None:
    return runtime().from_install(install_root)


def managed_environments() -> list[BlenderEnvironment]:
    return runtime().managed_environments()


__all__ = [
    "BlenderEnvironment",
    "BlenderRuntime",
    "runtime",
    "discover_default_environment",
    "resolve_environment_from_python",
    "resolve_environment_from_install",
    "managed_environments",
]
