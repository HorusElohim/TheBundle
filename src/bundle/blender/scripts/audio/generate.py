# Copyright 2025 HorusElohim
# Apache 2.0 License

from __future__ import annotations

import asyncio
import traceback
from pathlib import Path

import aud
import bpy
import numpy as np

from bundle.core import data, logger

FILE_NAME = "audio_scene6.blend"


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


def load_config(
    path: str | Path = r"C:\Dev\TheBundle\src\bundle\blender\scripts\audio\configuration.json",
) -> AudioDriverConfig:
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
        if s.type == "SOUND":
            scene.sequence_editor.sequences.remove(s)

    scene.sequence_editor.sequences.new_sound(
        name="Audio",
        filepath=audio_path,
        channel=1,
        frame_start=scene.frame_start,
    )

    scene.sync_mode = "AUDIO_SYNC"
    scene.use_audio_scrub = True
    scene.use_audio = True
    log.info(f"✅ Audio strip added to VSE: {audio_path}")


# --------------------------------------------------------------------------- #
# GEOMETRY NODES (Grid + Ripple) + Set Material
# --------------------------------------------------------------------------- #


def build_audio_grid_group(name: str = "AudioGridRipple") -> bpy.types.NodeTree:
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")

    # Interface sockets
    geo_in = ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    geo_out = ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    s_audio = ng.interface.new_socket("AudioDrive", in_out="INPUT", socket_type="NodeSocketFloat")
    s_audio.default_value = 0.0
    s_sx = ng.interface.new_socket("Grid Size X", in_out="INPUT", socket_type="NodeSocketFloat")
    s_sx.default_value = 10.0
    s_sy = ng.interface.new_socket("Grid Size Y", in_out="INPUT", socket_type="NodeSocketFloat")
    s_sy.default_value = 10.0
    s_rx = ng.interface.new_socket("Resolution X", in_out="INPUT", socket_type="NodeSocketInt")
    s_rx.default_value = 120
    s_ry = ng.interface.new_socket("Resolution Y", in_out="INPUT", socket_type="NodeSocketInt")
    s_ry.default_value = 120
    s_rad = ng.interface.new_socket("Instance Radius", in_out="INPUT", socket_type="NodeSocketFloat")
    s_rad.default_value = 0.02

    # Ripple controls
    s_freq = ng.interface.new_socket("Frequency", in_out="INPUT", socket_type="NodeSocketFloat")
    s_freq.default_value = 3.0
    s_speed = ng.interface.new_socket("Speed", in_out="INPUT", socket_type="NodeSocketFloat")
    s_speed.default_value = 1.0
    s_amp = ng.interface.new_socket("Amplitude", in_out="INPUT", socket_type="NodeSocketFloat")
    s_amp.default_value = 1.0

    # Nodes
    n_in = ng.nodes.new("NodeGroupInput")
    n_in.location = (-1200, 0)
    n_out = ng.nodes.new("NodeGroupOutput")
    n_out.location = (1600, 0)

    n_grid = ng.nodes.new("GeometryNodeMeshGrid")
    n_grid.location = (-1000, 0)
    n_pts = ng.nodes.new("GeometryNodeMeshToPoints")
    n_pts.location = (-800, 0)
    n_pts.mode = "VERTICES"

    # Position → distance from origin (XY)
    n_pos = ng.nodes.new("GeometryNodeInputPosition")
    n_pos.location = (-1000, -250)
    n_sep = ng.nodes.new("ShaderNodeSeparateXYZ")
    n_sep.location = (-800, -250)
    n_combxy = ng.nodes.new("ShaderNodeCombineXYZ")
    n_combxy.location = (-600, -250)
    n_combxy.inputs["Z"].default_value = 0.0
    n_len = ng.nodes.new("ShaderNodeVectorMath")
    n_len.location = (-400, -250)
    n_len.operation = "LENGTH"

    n_time = ng.nodes.new("GeometryNodeInputSceneTime")
    n_time.location = (-1000, -500)

    n_mul_freq = ng.nodes.new("ShaderNodeMath")
    n_mul_freq.location = (-200, -250)
    n_mul_freq.operation = "MULTIPLY"
    n_mul_spd = ng.nodes.new("ShaderNodeMath")
    n_mul_spd.location = (-200, -500)
    n_mul_spd.operation = "MULTIPLY"
    n_sub = ng.nodes.new("ShaderNodeMath")
    n_sub.location = (0, -300)
    n_sub.operation = "SUBTRACT"
    n_sin = ng.nodes.new("ShaderNodeMath")
    n_sin.location = (200, -300)
    n_sin.operation = "SINE"

    n_mul_amp = ng.nodes.new("ShaderNodeMath")
    n_mul_amp.location = (400, -300)
    n_mul_amp.operation = "MULTIPLY"
    n_mul_audio = ng.nodes.new("ShaderNodeMath")
    n_mul_audio.location = (600, -300)
    n_mul_audio.operation = "MULTIPLY"

    n_combz = ng.nodes.new("ShaderNodeCombineXYZ")
    n_combz.location = (800, -200)
    n_set = ng.nodes.new("GeometryNodeSetPosition")
    n_set.location = (1000, 0)

    n_ico = ng.nodes.new("GeometryNodeMeshIcoSphere")
    n_ico.location = (-600, 200)
    n_inst = ng.nodes.new("GeometryNodeInstanceOnPoints")
    n_inst.location = (1200, 0)
    n_real = ng.nodes.new("GeometryNodeRealizeInstances")
    n_real.location = (1400, 0)
    n_setmat = ng.nodes.new("GeometryNodeSetMaterial")
    n_setmat.name = "SET_MAT"
    n_setmat.location = (1500, 0)

    # Links
    ng.links.new(n_in.outputs[s_sx.identifier], n_grid.inputs["Size X"])
    ng.links.new(n_in.outputs[s_sy.identifier], n_grid.inputs["Size Y"])
    ng.links.new(n_in.outputs[s_rx.identifier], n_grid.inputs["Vertices X"])
    ng.links.new(n_in.outputs[s_ry.identifier], n_grid.inputs["Vertices Y"])
    ng.links.new(n_grid.outputs["Mesh"], n_pts.inputs["Mesh"])

    ng.links.new(n_pos.outputs["Position"], n_sep.inputs["Vector"])
    ng.links.new(n_sep.outputs["X"], n_combxy.inputs["X"])
    ng.links.new(n_sep.outputs["Y"], n_combxy.inputs["Y"])
    ng.links.new(n_combxy.outputs["Vector"], n_len.inputs[0])

    ng.links.new(n_len.outputs[0], n_mul_freq.inputs[0])
    ng.links.new(n_in.outputs[s_freq.identifier], n_mul_freq.inputs[1])

    ng.links.new(n_time.outputs["Seconds"], n_mul_spd.inputs[0])
    ng.links.new(n_in.outputs[s_speed.identifier], n_mul_spd.inputs[1])

    ng.links.new(n_mul_freq.outputs[0], n_sub.inputs[0])
    ng.links.new(n_mul_spd.outputs[0], n_sub.inputs[1])
    ng.links.new(n_sub.outputs[0], n_sin.inputs[0])

    ng.links.new(n_sin.outputs[0], n_mul_amp.inputs[0])
    ng.links.new(n_in.outputs[s_amp.identifier], n_mul_amp.inputs[1])

    ng.links.new(n_mul_amp.outputs[0], n_mul_audio.inputs[0])
    ng.links.new(n_in.outputs[s_audio.identifier], n_mul_audio.inputs[1])

    ng.links.new(n_mul_audio.outputs[0], n_combz.inputs["Z"])
    ng.links.new(n_pts.outputs["Points"], n_set.inputs["Geometry"])
    ng.links.new(n_combz.outputs["Vector"], n_set.inputs["Offset"])

    ng.links.new(n_ico.outputs["Mesh"], n_inst.inputs["Instance"])
    ng.links.new(n_set.outputs["Geometry"], n_inst.inputs["Points"])
    ng.links.new(n_inst.outputs["Instances"], n_real.inputs["Geometry"])
    ng.links.new(n_real.outputs["Geometry"], n_setmat.inputs["Geometry"])
    ng.links.new(n_setmat.outputs["Geometry"], n_out.inputs[geo_out.identifier])

    ng.links.new(n_in.outputs[s_rad.identifier], n_ico.inputs["Radius"])

    return ng


# --------------------------------------------------------------------------- #
# SHADER: Neon Emission + driver target
# --------------------------------------------------------------------------- #


def build_neon_shader(name: str = "NeonAudioMaterial") -> tuple[bpy.types.Material, bpy.types.ShaderNodeValue]:
    log.info(f"🎨 Creating neon emission shader: {name}")
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
    ramp.color_ramp.elements[0].color = (0.15, 0.00, 0.35, 1.0)  # deep purple
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.00, 1.00, 1.00, 1.0)  # cyan
    e3 = ramp.color_ramp.elements.new(0.92)
    e3.color = (1.00, 0.00, 0.60, 1.0)  # hot pink

    # Driver target (we will drive this with Empty.z)
    val = nodes.new("ShaderNodeValue")
    val.location = (200, -100)
    val.name = "AudioDrive_Value"
    val.outputs[0].default_value = 0.0

    mul = nodes.new("ShaderNodeMath")
    mul.location = (400, -100)
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 20.0  # emission boost

    # Links
    links.new(diffuse.outputs["BSDF"], storgb.inputs["Shader"])
    links.new(storgb.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], emission.inputs["Color"])
    links.new(mul.outputs["Value"], emission.inputs["Strength"])
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    links.new(val.outputs["Value"], mul.inputs[0])

    log.info(f"✅ Neon shader created: {name}")
    return mat, val


def add_driver_to_material_value(
    mat: bpy.types.Material,
    value_node: bpy.types.ShaderNodeValue,
    source_obj: bpy.types.Object,
    scale: float = 1.0,
) -> bpy.types.Driver:
    """Drive the material Value node with Empty.z"""
    path = f'nodes["{value_node.name}"].outputs[0].default_value'
    drv = mat.node_tree.driver_add(path).driver
    drv.type = "SCRIPTED"
    drv.expression = f"max(var*{scale:.6g}, 0.0)"

    var = drv.variables.new()
    var.name = "var"
    var.type = "TRANSFORMS"
    targ = var.targets[0]
    targ.id = source_obj
    targ.transform_type = "LOC_Z"
    targ.transform_space = "WORLD_SPACE"

    log.info(f"🔗 Material driver added: {mat.name}.{path} ← {source_obj.name}.LOC_Z (×{scale})")
    return drv


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

        # Build neon shader and assign it via Set Material in the GN tree
        mat, val_node = build_neon_shader()
        set_mat_node = next((n for n in ng.nodes if n.name == "SET_MAT"), None)
        if set_mat_node is None:
            raise RuntimeError("SET_MAT node not found in GN tree")
        set_mat_node.inputs["Material"].default_value = mat
        log.info("🎯 Material assigned via GN 'Set Material'")

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

        # Ensure channel visible in UI
        empty.location.z = 0.0
        empty.keyframe_insert(data_path="location", index=2, frame=bpy.context.scene.frame_start)

        samples_per_frame = int(rate / fps)
        fcu = empty.animation_data.action.fcurves.find("location", index=2) or empty.animation_data.action.fcurves.new(
            "location", index=2
        )
        fcu.keyframe_points.clear()

        log.info("📊 Baking audio amplitudes into keyframes")
        for f in range(n_frames):
            i0, i1 = f * samples_per_frame * channels, (f + 1) * samples_per_frame * channels
            frame = data[i0:i1]
            if channels > 1:
                # safe reshape
                cut = (frame.size // channels) * channels
                mono = frame[:cut].reshape(-1, channels).mean(axis=1) if cut else frame
            else:
                mono = frame
            amp = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
            fcu.keyframe_points.insert(frame=f + 1, value=amp)
        fcu.update()
        log.info(f"✅ Baked {n_frames} frames into Empty.location.z")

        # Driver for GN input
        log.info("⚙️ Connecting driver Empty.z → GN input")
        user_keys = [k for k in mod.keys() if not str(k).startswith("_")]
        if not user_keys:
            raise RuntimeError("No exposed GN inputs on modifier to drive")
        gn_key = user_keys[0]
        drv = obj.driver_add(f'modifiers["{mod.name}"]["{gn_key}"]').driver
        drv.type = "SCRIPTED"
        drv.expression = f"max(var*{cfg.amp_scale}, 0.0)"
        var = drv.variables.new()
        var.name, var.type = "var", "TRANSFORMS"
        var.targets[0].id = empty
        var.targets[0].transform_type = "LOC_Z"
        var.targets[0].transform_space = "WORLD_SPACE"

        # Driver for material emission strength (via Value node)
        add_driver_to_material_value(mat, val_node, empty, scale=cfg.amp_scale * 20.0)

        # VSE + Render settings
        add_audio_to_vse(str(audio_file))

        # Save
        bpy.ops.wm.save_as_mainfile(filepath=FILE_NAME)
        log.info(f"💾 Saved Blender project as {FILE_NAME}")
        log.info("✅ Phase 2 complete: ripple grid + neon material, both audio-driven!")

    except Exception:
        log.error("💥 Script failed", exc_info=True)
        traceback.print_exc()


if __name__ == "__main__":
    main()
