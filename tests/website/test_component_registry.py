from fastapi import APIRouter

from bundle.website import components
from bundle.website.components.websocket import ecc, heartbeat, toast
from bundle.website.components.websocket.base import WebSocketComponentParams


def test_websocket_component_defaults():
    default = heartbeat.WebSocketHeartbeatComponent()
    assert default.slug == "ws-heartbeat"
    assert default.params.endpoint == "/ws/heartbeat"
    assert any(asset.path.endswith("heartbeat/frontend/ws.js") for asset in default.assets)
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
