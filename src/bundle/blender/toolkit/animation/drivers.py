"""Driver helpers for Blender animations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bundle.core import logger, tracer

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import Driver, Material, Modifier, Object, ShaderNodeValue

log = logger.get_logger(__name__)


def _require_bpy() -> None:
    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")


@tracer.Sync.decorator.call_raise
def drive_property(
    id_data: Object | Material,
    data_path: str,
    source_obj: Object,
    *,
    scale: float = 1.0,
    transform: str = "LOC_Z",
    clamp_min: float = 0.0,
) -> Driver:
    """Attach a driver reading the given transform component of `source_obj`."""

    _require_bpy()
    driver = id_data.driver_add(data_path).driver
    driver.type = "SCRIPTED"
    driver.expression = f"max(var*{scale:.6g}, {clamp_min:.6g})"

    var = driver.variables.new()
    var.name = "var"
    var.type = "TRANSFORMS"
    target = var.targets[0]
    target.id = source_obj
    target.transform_type = transform
    target.transform_space = "WORLD_SPACE"

    log.info(
        "Driver attached: %s → %s (scale=%s)",
        source_obj.name,
        data_path,
        scale,
    )
    return driver


@tracer.Sync.decorator.call_raise
def drive_modifier_socket(
    obj: Object,
    modifier: Modifier,
    socket_name: str,
    source_obj: Object,
    *,
    scale: float = 1.0,
) -> Driver:
    """Drive a geometry nodes socket on `modifier` using `source_obj`."""

    path = f'modifiers["{modifier.name}"]["{socket_name}"]'
    return drive_property(obj, path, source_obj, scale=scale)


@tracer.Sync.decorator.call_raise
def drive_material_value(
    material: Material,
    value_node: ShaderNodeValue,
    source_obj: Object,
    *,
    scale: float = 1.0,
) -> Driver:
    """Drive a material value node with the transform of `source_obj`."""

    path = f'nodes["{value_node.name}"].outputs[0].default_value'
    return drive_property(material, path, source_obj, scale=scale)
