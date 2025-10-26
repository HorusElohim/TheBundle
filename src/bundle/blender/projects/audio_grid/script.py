"""Blender-side script for the audio grid project."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from bundle.core import logger, tracer

from ..toolkit.adapters.context import blender_logging_context
from ..toolkit.animation import drivers, keyframes
from ..toolkit.geometry.primitives import ensure_mesh
from ..toolkit.geometry.nodes import build_audio_grid_group
from ..toolkit.io.audio import add_sound_strip, sample_audio_envelope
from ..toolkit.materials.library import build_neon_audio_material
from .config import AudioGridConfig

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import Modifier, NodeTree, Object

log = logger.get_logger(__name__)

_DEFAULT_BLEND = Path("audio_scene6.blend")


def _require_bpy() -> None:
    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")


@tracer.Sync.decorator.call_raise
def _setup_geometry(config: AudioGridConfig) -> tuple[Object, Modifier, NodeTree]:
    obj = ensure_mesh(config.object_name)
    modifier = obj.modifiers.new("AudioDriver", type="NODES")
    node_group = build_audio_grid_group()
    modifier.node_group = node_group
    log.info("Audio grid geometry nodes attached to %s", obj.name)
    return obj, modifier, node_group


@tracer.Sync.decorator.call_raise
def _setup_material(node_group: NodeTree):
    material, value_node = build_neon_audio_material()
    set_mat = next((n for n in node_group.nodes if n.name == "SET_MAT"), None)
    if set_mat is None:
        raise RuntimeError("SET_MAT node not found in geometry node group")
    set_mat.inputs["Material"].default_value = material
    log.info("Neon material assigned through geometry nodes")
    return material, value_node


@tracer.Sync.decorator.call_raise
def _create_driver_empty() -> Object:
    _require_bpy()
    empty = bpy.data.objects.new("AudioEnvelope", None)
    bpy.context.collection.objects.link(empty)
    empty.location.z = 0.0
    log.info("Driver helper empty created: %s", empty.name)
    return empty


@tracer.Sync.decorator.call_raise
def _resolve_socket_name(modifier: Modifier) -> str:
    user_keys = [key for key in modifier.keys() if not str(key).startswith("_")]
    if not user_keys:
        raise RuntimeError("Geometry nodes modifier exposes no user sockets")
    socket = user_keys[0]
    log.info("Driving geometry nodes socket: %s", socket)
    return socket


@tracer.Sync.decorator.call_raise
def run_pipeline(config: AudioGridConfig, *, blend_path: Path | None = None) -> None:
    _require_bpy()
    scene = bpy.context.scene

    obj, modifier, node_group = _setup_geometry(config)
    material, value_node = _setup_material(node_group)

    fps = config.fps or scene.render.fps
    audio_path = config.resolved_audio_path()
    envelope, rate, channels = sample_audio_envelope(
        audio_path,
        fps=fps,
        frame_count=config.frame_count,
        normalize=config.normalize,
        smooth_window=config.smooth,
    )
    log.info("Audio envelope ready: fps=%s rate=%s channels=%s", fps, rate, channels)

    empty = _create_driver_empty()
    keyframes.bake_to_fcurve(
        empty,
        data_path="location",
        index=2,
        values=envelope,
        start_frame=scene.frame_start,
    )

    socket_name = _resolve_socket_name(modifier)
    drivers.drive_modifier_socket(obj, modifier, socket_name, empty, scale=config.amp_scale)
    drivers.drive_material_value(material, value_node, empty, scale=config.amp_scale * 20.0)

    add_sound_strip(audio_path, scene=scene)

    target = blend_path or _DEFAULT_BLEND
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    log.info("Blender project saved to %s", target)


@tracer.Sync.decorator.call_raise
def main(config_path: str | Path | None = None) -> None:
    _require_bpy()
    with blender_logging_context("audio_grid"):
        config = asyncio.run(AudioGridConfig.load(config_path))
        run_pipeline(config)


if __name__ == "__main__":  # pragma: no cover - Blender entrypoint
    main()