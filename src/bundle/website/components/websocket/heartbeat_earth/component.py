from ..base import WebSocketBaseComponent, WebSocketComponentParams


class WebSocketHeartBeatMonitorEarthComponent(WebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-heartbeat-earth"
    name: str = "HeartBeatMonitorEarth"
    description: str = "Futuristic Earth monitor for websocket heartbeat pulses."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/heartbeat-earth")
