from fastapi import APIRouter

from bundle.website.builtin import component as components
from bundle.website.builtin.component.graphic import (
    GraphicBaseComponent,
    GraphicThreeDComponent,
    GraphicThreeDComponentParams,
    GraphicTwoDComponent,
)
from bundle.website.builtin.component.websocket import heartbeat, heartbeat_cardio, heartbeat_earth, ecc, toast
from bundle.website.builtin.component.websocket.base import GPXWebSocketBaseComponent, WebSocketComponentParams


def test_websocket_component_defaults():
    default = heartbeat.WebSocketHeartbeatComponent()
    assert default.slug == "ws-heartbeat"
    assert default.params.endpoint == "/ws/heartbeat"
    assert any(asset.path.endswith("heartbeat/component.js") for asset in default.assets)
    assert all(asset.route_name == "components_static" for asset in default.assets)


def test_component_context_supports_data_params_override():
    custom = heartbeat.WebSocketHeartbeatComponent(params=WebSocketComponentParams(endpoint="/ws/custom"))
    ctx = components.context(custom)
    selected = ctx["components"]
    assert len(selected) == 1
    assert selected[0].params is not None and selected[0].params.endpoint == "/ws/custom"


def test_component_context_accepts_component_instance():
    custom = ecc.WebSocketECCComponent(params=WebSocketComponentParams(endpoint="/ws/ecc-alt"))
    ctx = components.context(custom)
    selected = ctx["components"]
    assert len(selected) == 1
    assert selected[0].slug == "ws-ecc"
    assert selected[0].params.endpoint == "/ws/ecc-alt"


def test_attach_routes_is_page_scoped():
    router = APIRouter()
    components.attach_routes(router, heartbeat.WebSocketHeartbeatComponent())
    paths = {route.path for route in router.routes}
    assert "/ws/heartbeat" in paths
    assert "/ws/toast" not in paths
    assert "/ws/ecc" not in paths


def test_attach_routes_supports_multiple_ecc_instances():
    router = APIRouter()
    components.attach_routes(
        router,
        ecc.WebSocketECCComponent(params=WebSocketComponentParams(endpoint="/ws/ecc-1")),
        ecc.WebSocketECCComponent(params=WebSocketComponentParams(endpoint="/ws/ecc-2")),
    )
    paths = {route.path for route in router.routes}
    assert "/ws/ecc-1" in paths
    assert "/ws/ecc-2" in paths


def test_graphic_component_exports_are_available():
    assert components.graphic.GraphicBaseComponent is GraphicBaseComponent
    assert components.graphic.GraphicTwoDComponent is GraphicTwoDComponent
    assert components.graphic.GraphicThreeDComponent is GraphicThreeDComponent


def test_graphic_3d_default_params():
    component = GraphicThreeDComponent(slug="graphic-3d")
    assert isinstance(component.params, GraphicThreeDComponentParams)
    assert component.params.render_mode == "3d"
    assert component.params.camera_mode == "orbit"


def test_gpx_websocket_base_inherits_graphic_3d_defaults():
    component = heartbeat_earth.WebSocketHeartBeatMonitorEarthComponent()
    assert isinstance(component, GPXWebSocketBaseComponent)
    assert component.params.render_mode == "3d"
    assert component.params.graph_id == "heartbeat-earth"


def test_heartbeat_cardio_component_defaults():
    component = heartbeat_cardio.WebSocketHeartBeatCardioComponent()
    assert isinstance(component, GPXWebSocketBaseComponent)
    assert component.slug == "ws-heartbeat-cardio"
    assert component.params.endpoint == "/ws/heartbeat-cardio"
    assert component.params.graph_id == "heartbeat-cardio"
