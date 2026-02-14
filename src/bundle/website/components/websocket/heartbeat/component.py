from ..base.component import register_websocket_component
from .backend import router

component = register_websocket_component(
    component_file=__file__,
    slug="ws-heartbeat",
    name="WebSocket Heartbeat",
    description="Periodic keepalive loop with a minimal UI.",
    router=router,
    ws_path="/ws/heartbeat",
)
