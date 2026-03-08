from ..base import WebSocketBaseComponent, WebSocketComponentParams


class WebSocketHeartbeatComponent(WebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-heartbeat"
    name: str = "WebSocket Heartbeat"
    description: str = "Periodic keepalive loop with a minimal UI."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/heartbeat")
