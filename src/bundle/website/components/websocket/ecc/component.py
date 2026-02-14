from ..base import WebSocketBaseComponent, WebSocketComponentParams


class WebSocketECCComponent(WebSocketBaseComponent):
    component_file: str = __file__
    slug: str = "ws-ecc"
    name: str = "WebSocket ECC monitor"
    description: str = "Monitor TX/RX keepalive pulses and timing."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/ecc")
