from __future__ import annotations

from ...graphic.threeD import GraphicThreeDComponent, GraphicThreeDComponentParams
from .component import WebSocketBaseComponent, WebSocketComponentParams

__doc__ = """
Graph (GPX) websocket base component.

Use this for components that render graph/3D-like visualizations and still
follow the standard websocket keepalive lifecycle.
"""


class GPXComponentParams(GraphicThreeDComponentParams, WebSocketComponentParams):
    """Shared params for GPX websocket components."""

    graph_id: str = "gpx"


class GPXWebSocketBaseComponent(WebSocketBaseComponent, GraphicThreeDComponent):
    """Base class for graph-oriented websocket components."""

    params: GPXComponentParams | None = None
