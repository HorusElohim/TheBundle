from ..base import GPXComponentParams, GPXWebSocketBaseComponent


class WebSocketHeartBeatCardioComponent(GPXWebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-heartbeat-cardio"
    name: str = "HeartBeatCardio"
    description: str = "3D cardiogram monitor for websocket heartbeat pulses."
    params: GPXComponentParams = GPXComponentParams(endpoint="/ws/heartbeat-cardio", graph_id="heartbeat-cardio")
