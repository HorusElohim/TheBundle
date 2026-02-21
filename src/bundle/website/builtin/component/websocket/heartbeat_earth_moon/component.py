from ..base import GPXComponentParams, GPXWebSocketBaseComponent


class WebSocketHeartBeatMonitorEarthMoonComponent(GPXWebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-heartbeat-earth-moon"
    name: str = "HeartBeatMonitorEarthMoon"
    description: str = "Heartbeat monitor with Earth moon scene (server moon, client heart)."
    params: GPXComponentParams = GPXComponentParams(endpoint="/ws/heartbeat-earth-moon", graph_id="heartbeat-earth-moon")
