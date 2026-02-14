from ..base import WebSocketBaseComponent, WebSocketComponentParams


class WebSocketHeartBeatMonitorEarthMoonComponent(WebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-heartbeat-earth-moon"
    name: str = "HeartBeatMonitorEarthMoon"
    description: str = "Heartbeat monitor with Earth moon scene (server moon, client heart)."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/heartbeat-earth-moon")
