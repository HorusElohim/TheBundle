from ..base import GPXComponentParams, GPXWebSocketBaseComponent


class WebSocketHeartBeatMonitorEarthComponent(GPXWebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-heartbeat-earth"
    name: str = "HeartBeatMonitorEarth"
    description: str = "Futuristic Earth monitor for websocket heartbeat pulses."
    params: GPXComponentParams = GPXComponentParams(endpoint="/ws/heartbeat-earth", graph_id="heartbeat-earth")
