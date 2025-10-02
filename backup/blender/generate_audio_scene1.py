from __future__ import annotations
from pathlib import Path

import numpy as np
import aud
import bpy
import asyncio
from bundle.core import logger
from bundle.core import data


class AudioDriverConfig(data.Data):
    audio: Path = data.Field(default_factory=Path)
    object: None | str = None
    frames: str = "auto"
    fps: None | int = None
    amp_scale: float = 5.0
    normalize: float = 0.98
    smooth: int = 0


log = logger.get_logger(__name__)


# ------------------------------- UTILITIES ---------------------------------- #


def load_config(path: str | Path = r"C:\Dev\TheBundle\src\bundle\blender\audio_configuration.json") -> AudioDriverConfig:
    cfg = asyncio.run(AudioDriverConfig.from_json(Path(path)))
    log.info(f"Loaded config: {cfg}")
    return cfg


def ensure_target_mesh(name_hint: str | None) -> bpy.types.Object:
    obj = bpy.context.active_object
    if name_hint:
        obj = bpy.data.objects.get(name_hint) or obj
    if not obj or obj.type != "MESH":
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        obj = bpy.context.active_object
        obj.name = name_hint or "AudioDrivenPlane"
    return obj


# ------------------------------- MAIN --------------------------------------- #


def main():
    cfg = load_config()

    # Target mesh
    obj = ensure_target_mesh(cfg.object)
    log.info(f"Target mesh: {obj.name}")

    # Build GN group
    ng = bpy.data.node_groups.new("AudioDrivenWave", "GeometryNodeTree")
    float_in = ng.interface.new_socket("AudioDrive", in_out="INPUT", socket_type="NodeSocketFloat")
    float_in.default_value = 0.0

    n_in = ng.nodes.new("NodeGroupInput")
    n_out = ng.nodes.new("NodeGroupOutput")
    n_set = ng.nodes.new("GeometryNodeSetPosition")
    n_norm = ng.nodes.new("GeometryNodeInputNormal")
    n_mulv = ng.nodes.new("ShaderNodeVectorMath")
    n_mulv.operation = "MULTIPLY"
    n_muls = ng.nodes.new("ShaderNodeMath")
    n_muls.operation = "MULTIPLY"

    ng.links.new(n_in.outputs[0], n_set.inputs["Geometry"])
    ng.links.new(n_set.outputs["Geometry"], n_out.inputs[0])
    ng.links.new(n_in.outputs[float_in.identifier], n_muls.inputs[0])
    n_muls.inputs[1].default_value = 1.0
    ng.links.new(n_norm.outputs["Normal"], n_mulv.inputs[0])
    ng.links.new(n_muls.outputs[0], n_mulv.inputs[1])
    ng.links.new(n_mulv.outputs["Vector"], n_set.inputs["Offset"])

    mod = obj.modifiers.new("AudioDriver", type="NODES")
    mod.node_group = ng

    # Audio decode
    audio_file = Path(cfg.audio)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio not found: {audio_file}")
    snd = aud.Sound.file(str(audio_file))
    rate, channels = snd.specs
    data = np.asarray(snd.data(), dtype=np.float32).ravel()

    fps = cfg.fps or bpy.context.scene.render.fps
    total_frames = data.size // (rate * channels)
    if cfg.frames == "auto":
        n_frames = int(total_frames * fps)
    else:
        n_frames = int(cfg.frames)
    log.info(f"Audio length frames={n_frames} @ {fps}fps, rate={rate}Hz")

    # Bake amplitudes to Empty
    empty = bpy.data.objects.new("AudioEmpty", None)
    bpy.context.collection.objects.link(empty)
    if not empty.animation_data:
        empty.animation_data_create()
    if not empty.animation_data.action:
        empty.animation_data.action = bpy.data.actions.new(name="AudioEmptyAction")

    samples_per_frame = int(rate / fps)
    fcu = empty.animation_data.action.fcurves.new("location", index=2)
    fcu.keyframe_points.clear()

    for f in range(n_frames):
        i0, i1 = f * samples_per_frame * channels, (f + 1) * samples_per_frame * channels
        frame = data[i0:i1]
        if channels > 1:
            frame = frame.reshape(-1, channels).mean(axis=1)
        amp = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
        fcu.keyframe_points.insert(frame=f + 1, value=amp)
    fcu.update()

    # Driver wiring
    key = list(k for k in mod.keys() if not k.startswith("_"))[0]
    drv = obj.driver_add(f'modifiers["{mod.name}"]["{key}"]').driver
    drv.type = "SCRIPTED"
    drv.expression = f"max(var*{cfg.amp_scale}, 0.0)"
    var = drv.variables.new()
    var.name, var.type = "var", "TRANSFORMS"
    var.targets[0].id = empty
    var.targets[0].transform_type = "LOC_Z"
    var.targets[0].transform_space = "WORLD_SPACE"

    log.info("✅ AudioDriver connected: Empty.z → GeometryNodes.AudioDrive")


if __name__ == "__main__":
    main()
