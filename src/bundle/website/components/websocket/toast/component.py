from ..base.component import register_websocket_component

component = register_websocket_component(
    component_file=__file__,
    slug="ws-toast",
    name="WebSocket Toast Feed",
    description="Toast notifications for incoming messages.",
)
