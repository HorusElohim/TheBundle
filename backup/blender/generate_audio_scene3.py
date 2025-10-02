# Copyright 2025 HorusElohim
# Apache 2.0 License

from __future__ import annotations
from pathlib import Path
import traceback
import asyncio

import numpy as np
import aud
import bpy

from bundle.core import logger, data


class AudioDriverConfig(data.Data):
    audio: Path = data.Field(default_factory=Path)
    object: None | str = None
    frames: str = "auto"
    fps: None | int = None
    amp_scale: float = 5.0
    normalize: float = 0.98
    smooth: int = 0


log = logger.get_logger(__name__)
log.parent = logger.get_logger("bundle")

# --------------------------------------------------------------------------- #
# UTILITIES
# --------------------------------------------------------------------------- #

def load_config(path: str | Path = r"C:\Dev\TheBundle\src\bundle\blender\audio_configuration.json") -> AudioDriverConfig:
    log.info(f"📂 Loading configuration from {path}")
    cfg = asyncio.run(AudioDriverConfig.from_json(Path(path)))
    log.info(f"✅ Loaded config: {cfg}")
    return cfg


def ensure_target_mesh(name_hint: str | None) -> bpy.types.Object:
    log.info(f"🔍 Ensuring target mesh (hint={name_hint})")
    obj = bpy.context.active_object
    if name_hint:
        obj = bpy.data.objects.get(name_hint) or obj
    if not obj or obj.type != "MESH":
        log.info("ℹ️ No mesh found, creating plane")
        bpy.ops.mesh.primitive_plane_add(size=2.0)
        obj = bpy.context.active_object
        obj.name = name_hint or "AudioDrivenPlane"
    log.info(f"✅ Target mesh: {obj.name}")
    return obj


def add_audio_to_vse(audio_path: str):
    scene = bpy.context.scene
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    for s in list(scene.sequence_editor.sequences_all):
        if s.type == 'SOUND':
            scene.sequence_editor.sequences.remove(s)

    scene.sequence_editor.sequences.new_sound(
        name="Audio",
        filepath=audio_path,
        channel=1,
        frame_start=scene.frame_start,
    )

    scene.sync_mode = 'AUDIO_SYNC'
    scene.use_audio_scrub = True
    scene.use_audio = True

    log.info(f"✅ Audio strip added to VSE: {audio_path}")


# --------------------------------------------------------------------------- #
# GEOMETRY NODES BUILDER: GRID SYSTEM
# --------------------------------------------------------------------------- #

def build_audio_grid_group(name: str = "AudioGridSystem") -> bpy.types.NodeTree:
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")

    # Interface
    geo_in  = ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type='NodeSocketGeometry')
    geo_out = ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type='NodeSocketGeometry')
    s_audio = ng.interface.new_socket("AudioDrive",   in_out="INPUT", socket_type='NodeSocketFloat'); s_audio.default_value = 0.0
    s_sx    = ng.interface.new_socket("Grid Size X",  in_out="INPUT", socket_type='NodeSocketFloat'); s_sx.default_value = 10.0
    s_sy    = ng.interface.new_socket("Grid Size Y",  in_out="INPUT", socket_type='NodeSocketFloat'); s_sy.default_value = 10.0
    s_rx    = ng.interface.new_socket("Resolution X", in_out="INPUT", socket_type='NodeSocketInt');   s_rx.default_value = 120
    s_ry    = ng.interface.new_socket("Resolution Y", in_out="INPUT", socket_type='NodeSocketInt');   s_ry.default_value = 120
    s_rad   = ng.interface.new_socket("Instance Radius", in_out="INPUT", socket_type='NodeSocketFloat'); s_rad.default_value = 0.02

    # Nodes
    n_in   = ng.nodes.new("NodeGroupInput");        n_in.location = (-900, 0)
    n_out  = ng.nodes.new("NodeGroupOutput");       n_out.location = ( 600, 0)

    n_grid = ng.nodes.new("GeometryNodeMeshGrid");  n_grid.location = (-700, 60)
    n_pts  = ng.nodes.new("GeometryNodeMeshToPoints"); n_pts.location = (-450, 60); n_pts.mode = 'VERTICES'

    n_set  = ng.nodes.new("GeometryNodeSetPosition"); n_set.location = (-200, 60)
    n_comb = ng.nodes.new("ShaderNodeCombineXYZ");     n_comb.location = (-400, -140)
    n_mul  = ng.nodes.new("ShaderNodeMath");           n_mul.location  = (-600, -140); n_mul.operation = 'MULTIPLY'

    n_ico  = ng.nodes.new("GeometryNodeMeshIcoSphere"); n_ico.location = (-200, -240)
    n_inst = ng.nodes.new("GeometryNodeInstanceOnPoints"); n_inst.location = (50, 60)
    n_real = ng.nodes.new("GeometryNodeRealizeInstances"); n_real.location = (300, 60)

    # Connections
    ng.links.new(n_in.outputs[s_sx.identifier], n_grid.inputs["Size X"])
    ng.links.new(n_in.outputs[s_sy.identifier], n_grid.inputs["Size Y"])
    ng.links.new(n_in.outputs[s_rx.identifier], n_grid.inputs["Vertices X"])
    ng.links.new(n_in.outputs[s_ry.identifier], n_grid.inputs["Vertices Y"])
    ng.links.new(n_grid.outputs["Mesh"], n_pts.inputs["Mesh"])
    ng.links.new(n_pts.outputs["Points"], n_set.inputs["Geometry"])
    ng.links.new(n_in.outputs[s_audio.identifier], n_mul.inputs[0])
    ng.links.new(n_mul.outputs[0], n_comb.inputs["Z"])
    ng.links.new(n_comb.outputs["Vector"], n_set.inputs["Offset"])
    ng.links.new(n_ico.outputs["Mesh"], n_inst.inputs["Instance"])
    ng.links.new(n_set.outputs["Geometry"], n_inst.inputs["Points"])
    ng.links.new(n_inst.outputs["Instances"], n_real.inputs["Geometry"])
    ng.links.new(n_real.outputs["Geometry"], n_out.inputs[geo_out.identifier])
    ng.links.new(n_in.outputs[s_rad.identifier], n_ico.inputs["Radius"])

    return ng


# --------------------------------------------------------------------------- #
# MAIN
# --------------------------------------------------------------------------- #

def main():
    try:
        cfg = load_config()
        obj = ensure_target_mesh(cfg.object)

        # Geometry Nodes
        log.info("🎛 Building Audio Grid GeometryNodes")
        ng = build_audio_grid_group()
        mod = obj.modifiers.new("AudioDriver", type="NODES")
        mod.node_group = ng
        log.info("✅ Geometry Nodes (grid instancer) attached")

        # Audio decode
        audio_file = Path(cfg.audio)
        log.info(f"🎵 Loading audio: {audio_file}")
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio not found: {audio_file}")
        snd = aud.Sound.file(str(audio_file))
        rate, channels = snd.specs
        data = np.asarray(snd.data(), dtype=np.float32).ravel()
        log.info(f"✅ Audio loaded (rate={rate}, channels={channels}, samples={len(data)})")

        fps = cfg.fps or bpy.context.scene.render.fps
        total_frames = data.size // (rate * channels)
        n_frames = int(total_frames * fps) if cfg.frames == "auto" else int(cfg.frames)
        log.info(f"🎬 Using {n_frames} frames @ {fps} fps")

        # Empty with baked audio
        log.info("📌 Creating Empty for animation")
        empty = bpy.data.objects.new("AudioEmpty", None)
        bpy.context.collection.objects.link(empty)
        empty.animation_data_create()
        empty.animation_data.action = bpy.data.actions.new(name="AudioEmptyAction")

        samples_per_frame = int(rate / fps)
        fcu = empty.animation_data.action.fcurves.new("location", index=2)
        fcu.keyframe_points.clear()

        log.info("📊 Baking audio amplitudes into keyframes")
        for f in range(n_frames):
            i0, i1 = f * samples_per_frame * channels, (f + 1) * samples_per_frame * channels
            frame = data[i0:i1]
            if channels > 1:
                frame = frame.reshape(-1, channels).mean(axis=1)
            amp = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
            fcu.keyframe_points.insert(frame=f + 1, value=amp)
        fcu.update()
        log.info(f"✅ Baked {n_frames} frames into Empty.location.z")

        # Driver
        log.info("⚙️ Connecting driver Empty.z → GN input")
        key = list(k for k in mod.keys() if not k.startswith("_"))[0]
        drv = obj.driver_add(f'modifiers["{mod.name}"]["{key}"]').driver
        drv.type = "SCRIPTED"
        drv.expression = f"max(var*{cfg.amp_scale}, 0.0)"
        var = drv.variables.new()
        var.name, var.type = "var", "TRANSFORMS"
        var.targets[0].id = empty
        var.targets[0].transform_type = "LOC_Z"
        var.targets[0].transform_space = "WORLD_SPACE"

        # VSE
        log.info("🎬 Adding audio to VSE")
        add_audio_to_vse(str(audio_file))

        # Save
        bpy.ops.wm.save_as_mainfile(filepath="audio_scene3.blend")
        log.info("💾 Saved Blender project as audio_scene3.blend")
        log.info("✅ Phase 1 complete: grid system + audio driver ready!")

    except Exception:
        log.error("💥 Script failed", exc_info=True)
        traceback.print_exc()


if __name__ == "__main__":
    main()
