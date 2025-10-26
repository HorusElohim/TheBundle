"""Keyframe helpers for Blender animations."""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from bundle.core import logger, tracer

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import FCurve, Object

log = logger.get_logger(__name__)


def _require_bpy() -> None:
    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")


@tracer.Sync.decorator.call_raise
def bake_to_fcurve(
    obj: Object,
    *,
    data_path: str,
    index: int,
    values: Iterable[float],
    start_frame: int = 1,
) -> FCurve:
    """Replace the f-curve with keyframes for the provided values."""

    _require_bpy()
    samples = list(values)
    obj.animation_data_create()
    if obj.animation_data.action is None:
        obj.animation_data.action = bpy.data.actions.new(name=f"{obj.name}_Action")
    action = obj.animation_data.action

    fcurve = action.fcurves.find(data_path, index=index)
    if fcurve is None:
        fcurve = action.fcurves.new(data_path, index=index)
    fcurve.keyframe_points.clear()

    for offset, value in enumerate(samples):
        frame = start_frame + offset
        fcurve.keyframe_points.insert(frame=frame, value=value)

    fcurve.update()
    log.info("Baked %s frames into %s.%s[%s]", len(samples), obj.name, data_path, index)
    return fcurve