from __future__ import annotations
from pathlib import Path
import traceback

import numpy as np
import aud
import bpy
import asyncio
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


# ------------------------------- UTILITIES ---------------------------------- #

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

    # Ensure a sequence editor exists
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    # Remove old audio strips if any
    for s in list(scene.sequence_editor.sequences_all):
        if s.type == 'SOUND':
            scene.sequence_editor.sequences.remove(s)

    # Add new audio strip
    scene.sequence_editor.sequences.new_sound(
        name="Audio",
        filepath=audio_path,
        channel=1,
        frame_start=scene.frame_start,
    )

    # Enable audio playback
    scene.sync_mode = 'AUDIO_SYNC'
    scene.use_audio_scrub = True
    scene.use_audio = True

    log.info(f"✅ Audio strip added to VSE: {audio_path}")


# ------------------------------- MAIN --------------------------------------- #

def main():
    try:
        cfg = load_config()

        # Target mesh
        obj = ensure_target_mesh(cfg.object)

        # Build GN group
        log.info("🎛 Creating Geometry Nodes group")
        ng = bpy.data.node_groups.new("AudioDrivenWave", "GeometryNodeTree")

        # Interface sockets
        geo_in = ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        geo_out = ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        float_in = ng.interface.new_socket("AudioDrive", in_out="INPUT", socket_type="NodeSocketFloat")
        float_in.default_value = 0.0

        # Nodes
        n_in = ng.nodes.new("NodeGroupInput")
        n_out = ng.nodes.new("NodeGroupOutput")
        n_set = ng.nodes.new("GeometryNodeSetPosition")
        n_norm = ng.nodes.new("GeometryNodeInputNormal")
        n_mulv = ng.nodes.new("ShaderNodeVectorMath"); n_mulv.operation = "MULTIPLY"
        n_muls = ng.nodes.new("ShaderNodeMath"); n_muls.operation = "MULTIPLY"

        # Layout (optional)
        n_in.location = (-600, 0)
        n_set.location = (-300, 0)
        n_out.location = (200, 0)

        # Connections
        ng.links.new(n_in.outputs[geo_in.identifier], n_set.inputs["Geometry"])
        ng.links.new(n_set.outputs["Geometry"], n_out.inputs[geo_out.identifier])
        ng.links.new(n_in.outputs[float_in.identifier], n_muls.inputs[0])
        n_muls.inputs[1].default_value = 1.0
        ng.links.new(n_norm.outputs["Normal"], n_mulv.inputs[0])
        ng.links.new(n_muls.outputs[0], n_mulv.inputs[1])
        ng.links.new(n_mulv.outputs["Vector"], n_set.inputs["Offset"])

        mod = obj.modifiers.new("AudioDriver", type="NODES")
        mod.node_group = ng
        log.info("✅ Geometry Nodes modifier attached")

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
        if cfg.frames == "auto":
            n_frames = int(total_frames * fps)
        else:
            n_frames = int(cfg.frames)
        log.info(f"🎬 Using {n_frames} frames @ {fps} fps")

        # Bake amplitudes to Empty
        log.info("📌 Creating Empty for animation")
        empty = bpy.data.objects.new("AudioEmpty", None)
        bpy.context.collection.objects.link(empty)
        if not empty.animation_data:
            empty.animation_data_create()
        if not empty.animation_data.action:
            empty.animation_data.action = bpy.data.actions.new(name="AudioEmptyAction")

        # Initial keyframe
        empty.location.z = 0.0
        empty.keyframe_insert(data_path="location", index=2, frame=bpy.context.scene.frame_start)

        samples_per_frame = int(rate / fps)
        fcu = empty.animation_data.action.fcurves.find("location", index=2)
        if fcu is None:
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

        # Driver wiring
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

        # Add audio to VSE
        log.info("🎬 Adding audio to VSE")
        add_audio_to_vse(str(audio_file))

        # Save the project
        bpy.ops.wm.save_as_mainfile(filepath="audio_scene.blend")
        log.info("💾 Saved Blender project as audio_scene.blend")

        log.info("✅ AudioDriver connected successfully and ready to use!")

    except Exception as e:
        log.error("💥 Script failed", exc_info=True)
        traceback.print_exc()


if __name__ == "__main__":
    main()
