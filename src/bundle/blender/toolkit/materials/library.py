"""Material library for Blender toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bundle.core import logger, tracer

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import Material, ShaderNodeValue

log = logger.get_logger(__name__)


def _require_bpy() -> None:
    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")


@tracer.Sync.decorator.call_raise
def build_neon_audio_material(name: str = "NeonAudioMaterial") -> tuple[Material, ShaderNodeValue]:
    """Create the neon emission material used by the audio grid."""

    _require_bpy()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (800, 0)
    emission = nodes.new("ShaderNodeEmission")
    emission.location = (600, 0)

    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.location = (0, 200)
    diffuse.inputs["Roughness"].default_value = 0.0

    storgb = nodes.new("ShaderNodeShaderToRGB")
    storgb.location = (200, 200)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (400, 200)
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].color = (0.15, 0.00, 0.35, 1.0)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.00, 1.00, 1.00, 1.0)
    e3 = ramp.color_ramp.elements.new(0.92)
    e3.color = (1.00, 0.00, 0.60, 1.0)

    driver_value = nodes.new("ShaderNodeValue")
    driver_value.location = (200, -100)
    driver_value.name = "AudioDrive_Value"
    driver_value.outputs[0].default_value = 0.0

    mul = nodes.new("ShaderNodeMath")
    mul.location = (400, -100)
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 20.0

    links.new(diffuse.outputs["BSDF"], storgb.inputs["Shader"])
    links.new(storgb.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])
    links.new(mul.outputs["Value"], emission.inputs["Strength"])
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    links.new(driver_value.outputs["Value"], mul.inputs[0])

    log.info("Neon audio material created: %s", mat.name)
    return mat, driver_value
