"""Geometry primitives used across Blender toolkits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bundle.core import logger, tracer

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import Object

log = logger.get_logger(__name__)


@tracer.Sync.decorator.call_raise
def ensure_mesh(name_hint: str | None = None) -> Object:
    """Make sure a mesh object is available and return it."""

    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")

    obj = bpy.context.active_object
    if name_hint:
        candidate = bpy.data.objects.get(name_hint)
        if candidate is not None:
            obj = candidate

    if obj is None or obj.type != "MESH":
        log.info("Creating fallback plane mesh for audio driver")
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        obj = bpy.context.active_object
        if obj is None:
            raise RuntimeError("Unable to create plane mesh")
        obj.name = name_hint or "AudioDrivenPlane"
    else:
        log.debug("Reusing existing mesh: %s", obj.name)

    return obj
