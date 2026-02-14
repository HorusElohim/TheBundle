from ..base.component import register_websocket_component
from .backend import router

component = register_websocket_component(
    component_file=__file__,
    slug="ws-toast",
    name="WebSocket Toast Feed",
    description="Toast notifications for incoming messages.",
    router=router,
    ws_path="/ws/toast",
)
