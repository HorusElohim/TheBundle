"""Blender-side script: build a Blender scene from a 3DGS PLY.

Invoked headless by BlenderStage:
    blender --background --python ply_to_blend.py -- /path/to/params.json

Parameters are read from a JSON file whose path follows the ``--`` separator
in sys.argv.  All Blender API calls live here; the host never imports bpy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load params
# ---------------------------------------------------------------------------

_params_path = Path(sys.argv[sys.argv.index("--") + 1])
p = json.loads(_params_path.read_text(encoding="utf-8"))

ply_path: str = p["ply_path"]
blend_out: str = p["blend_out"]
render_out: str | None = p.get("render_out")
engine: str = p.get("engine", "EEVEE")
do_render: bool = p.get("do_render", False)

# ---------------------------------------------------------------------------
# Blender imports (only valid inside a Blender Python session)
# ---------------------------------------------------------------------------

import bpy

# ---------------------------------------------------------------------------
# Scene setup
# ---------------------------------------------------------------------------

bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.wm.ply_import(filepath=ply_path)

imported = bpy.context.selected_objects[:]
if imported:
    for obj in imported:
        obj.name = "GaussianSplat"
    bpy.context.view_layer.objects.active = imported[0]

    obj = imported[0]

    # -- Emission material --------------------------------------------------
    mat = bpy.data.materials.new("GaussianSplatMat")
    mat.use_nodes = True
    mt = mat.node_tree
    mt.nodes.clear()
    emit = mt.nodes.new("ShaderNodeEmission")
    mat_out = mt.nodes.new("ShaderNodeOutputMaterial")
    emit.inputs["Color"].default_value = (0.85, 0.85, 0.85, 1.0)
    emit.inputs["Strength"].default_value = 1.0
    mt.links.new(emit.outputs["Emission"], mat_out.inputs["Surface"])

    # -- Geometry Nodes: MeshToPoints → SetMaterial → InstanceOnPoints ------
    # PLY vertices have no faces and no material.  Build a GN tree that
    # converts the mesh to renderable icosphere instances so CYCLES can
    # shade them via the emission material.
    mod = obj.modifiers.new("GS_Points", type="NODES")
    ng = bpy.data.node_groups.new("GS_Points", "GeometryNodeTree")
    mod.node_group = ng

    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")

    ns, lk = ng.nodes, ng.links
    n_in = ns.new("NodeGroupInput")
    n_out = ns.new("NodeGroupOutput")
    m2p = ns.new("GeometryNodeMeshToPoints")
    sph = ns.new("GeometryNodeMeshIcoSphere")
    sph.inputs["Radius"].default_value = 0.008
    sph.inputs["Subdivisions"].default_value = 1
    set_mat = ns.new("GeometryNodeSetMaterial")
    set_mat.inputs["Material"].default_value = mat
    iop = ns.new("GeometryNodeInstanceOnPoints")
    realise = ns.new("GeometryNodeRealizeInstances")

    lk.new(n_in.outputs[0], m2p.inputs["Mesh"])
    lk.new(sph.outputs["Mesh"], set_mat.inputs["Geometry"])
    lk.new(set_mat.outputs["Geometry"], iop.inputs["Instance"])
    lk.new(m2p.outputs["Points"], iop.inputs["Points"])
    lk.new(iop.outputs["Instances"], realise.inputs["Geometry"])
    lk.new(realise.outputs["Geometry"], n_out.inputs[0])

# ---------------------------------------------------------------------------
# Optional render
# ---------------------------------------------------------------------------

if do_render and render_out:
    scene = bpy.context.scene

    # EEVEE requires a display/GPU context — fall back to CYCLES in headless mode.
    if bpy.app.background and engine == "EEVEE":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
    else:
        scene.render.engine = "BLENDER_" + engine

    scene.render.filepath = render_out + "/"
    scene.render.image_settings.file_format = "PNG"

    # Add a camera aimed at the world origin if none exists.
    if not any(o.type == "CAMERA" for o in scene.objects):
        from mathutils import Vector

        loc = Vector((3.0, -3.0, 2.0))
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.object
        direction = Vector((0, 0, 0)) - loc
        cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam

    # Add a sun light for CYCLES/EEVEE if none exists.
    if not any(o.type == "LIGHT" for o in scene.objects):
        bpy.ops.object.light_add(type="SUN", location=(5, 5, 5))

    bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------------------
# Save .blend
# ---------------------------------------------------------------------------

bpy.ops.wm.save_as_mainfile(filepath=blend_out)
print("recon3d-blender: saved", blend_out)
