"""Geometry node graphs bundled with the Blender toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bundle.core import logger, tracer

try:  # pragma: no cover - Blender-only dependency
    import bpy  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    bpy = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing helpers
    from bpy.types import Node, NodeSocket, NodeTree

log = logger.get_logger(__name__)


def _require_bpy() -> None:
    if bpy is None:  # pragma: no cover - executed outside Blender
        raise RuntimeError("bpy is not available; ensure this runs inside Blender")


def _socket(ng: NodeTree, label: str, *, in_out: str, socket_type: str, default=None) -> NodeSocket:
    socket = ng.interface.new_socket(label, in_out=in_out, socket_type=socket_type)
    if default is not None:
        socket.default_value = default
    return socket


def _node(ng: NodeTree, node_type: str, location: tuple[float, float]) -> Node:
    node = ng.nodes.new(node_type)
    node.location = location
    return node


@tracer.Sync.decorator.call_raise
def build_audio_grid_group(name: str = "AudioGridRipple") -> NodeTree:
    """Construct the geometry node group that instantiates the audio grid."""

    _require_bpy()
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")

    geo_in = _socket(ng, "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    geo_out = _socket(ng, "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    s_audio = _socket(ng, "AudioDrive", in_out="INPUT", socket_type="NodeSocketFloat", default=0.0)
    s_sx = _socket(ng, "Grid Size X", in_out="INPUT", socket_type="NodeSocketFloat", default=10.0)
    s_sy = _socket(ng, "Grid Size Y", in_out="INPUT", socket_type="NodeSocketFloat", default=10.0)
    s_rx = _socket(ng, "Resolution X", in_out="INPUT", socket_type="NodeSocketInt", default=120)
    s_ry = _socket(ng, "Resolution Y", in_out="INPUT", socket_type="NodeSocketInt", default=120)
    s_rad = _socket(ng, "Instance Radius", in_out="INPUT", socket_type="NodeSocketFloat", default=0.02)
    s_freq = _socket(ng, "Frequency", in_out="INPUT", socket_type="NodeSocketFloat", default=3.0)
    s_speed = _socket(ng, "Speed", in_out="INPUT", socket_type="NodeSocketFloat", default=1.0)
    s_amp = _socket(ng, "Amplitude", in_out="INPUT", socket_type="NodeSocketFloat", default=1.0)

    n_in = _node(ng, "NodeGroupInput", (-1200, 0))
    n_out = _node(ng, "NodeGroupOutput", (1600, 0))

    n_grid = _node(ng, "GeometryNodeMeshGrid", (-1000, 0))
    n_pts = _node(ng, "GeometryNodeMeshToPoints", (-800, 0))
    n_pts.mode = "VERTICES"

    n_pos = _node(ng, "GeometryNodeInputPosition", (-1000, -250))
    n_sep = _node(ng, "ShaderNodeSeparateXYZ", (-800, -250))
    n_mix_xy = _node(ng, "ShaderNodeCombineXYZ", (-600, -250))
    n_mix_xy.inputs["Z"].default_value = 0.0
    n_len = _node(ng, "ShaderNodeVectorMath", (-400, -250))
    n_len.operation = "LENGTH"

    n_time = _node(ng, "GeometryNodeInputSceneTime", (-1000, -500))
    n_mul_freq = _node(ng, "ShaderNodeMath", (-200, -250))
    n_mul_freq.operation = "MULTIPLY"
    n_mul_speed = _node(ng, "ShaderNodeMath", (-200, -500))
    n_mul_speed.operation = "MULTIPLY"
    n_sub = _node(ng, "ShaderNodeMath", (0, -300))
    n_sub.operation = "SUBTRACT"
    n_sin = _node(ng, "ShaderNodeMath", (200, -300))
    n_sin.operation = "SINE"
    n_mul_amp = _node(ng, "ShaderNodeMath", (400, -300))
    n_mul_amp.operation = "MULTIPLY"
    n_mul_audio = _node(ng, "ShaderNodeMath", (600, -300))
    n_mul_audio.operation = "MULTIPLY"

    n_offset = _node(ng, "ShaderNodeCombineXYZ", (800, -200))
    n_set_pos = _node(ng, "GeometryNodeSetPosition", (1000, 0))

    n_ico = _node(ng, "GeometryNodeMeshIcoSphere", (-600, 200))
    n_inst = _node(ng, "GeometryNodeInstanceOnPoints", (1200, 0))
    n_realize = _node(ng, "GeometryNodeRealizeInstances", (1400, 0))
    n_set_mat = _node(ng, "GeometryNodeSetMaterial", (1500, 0))
    n_set_mat.name = "SET_MAT"

    links = ng.links
    links.new(n_in.outputs[s_sx.identifier], n_grid.inputs["Size X"])
    links.new(n_in.outputs[s_sy.identifier], n_grid.inputs["Size Y"])
    links.new(n_in.outputs[s_rx.identifier], n_grid.inputs["Vertices X"])
    links.new(n_in.outputs[s_ry.identifier], n_grid.inputs["Vertices Y"])
    links.new(n_in.outputs[s_rad.identifier], n_ico.inputs["Radius"])

    links.new(n_grid.outputs["Mesh"], n_pts.inputs["Mesh"])
    links.new(n_pts.outputs["Points"], n_set_pos.inputs["Geometry"])
    links.new(n_set_pos.outputs["Geometry"], n_inst.inputs["Points"])

    links.new(n_pos.outputs["Position"], n_sep.inputs["Vector"])
    links.new(n_sep.outputs["X"], n_mix_xy.inputs["X"])
    links.new(n_sep.outputs["Y"], n_mix_xy.inputs["Y"])
    links.new(n_mix_xy.outputs["Vector"], n_len.inputs[0])

    links.new(n_len.outputs[0], n_mul_freq.inputs[0])
    links.new(n_in.outputs[s_freq.identifier], n_mul_freq.inputs[1])

    links.new(n_time.outputs["Seconds"], n_mul_speed.inputs[0])
    links.new(n_in.outputs[s_speed.identifier], n_mul_speed.inputs[1])

    links.new(n_mul_freq.outputs[0], n_sub.inputs[0])
    links.new(n_mul_speed.outputs[0], n_sub.inputs[1])
    links.new(n_sub.outputs[0], n_sin.inputs[0])

    links.new(n_sin.outputs[0], n_mul_amp.inputs[0])
    links.new(n_in.outputs[s_amp.identifier], n_mul_amp.inputs[1])

    links.new(n_mul_amp.outputs[0], n_mul_audio.inputs[0])
    links.new(n_in.outputs[s_audio.identifier], n_mul_audio.inputs[1])

    links.new(n_mul_audio.outputs[0], n_offset.inputs["Z"])
    links.new(n_offset.outputs["Vector"], n_set_pos.inputs["Offset"])

    links.new(n_ico.outputs["Mesh"], n_inst.inputs["Instance"])
    links.new(n_inst.outputs["Instances"], n_realize.inputs["Geometry"])
    links.new(n_realize.outputs["Geometry"], n_set_mat.inputs["Geometry"])
    links.new(n_set_mat.outputs["Geometry"], n_out.inputs[geo_out.identifier])

    log.info("Audio grid node group constructed: %s", ng.name)
    return ng