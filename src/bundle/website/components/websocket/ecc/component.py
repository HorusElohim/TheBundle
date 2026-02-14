from ..base.component import register_websocket_component
from .backend import router

component = register_websocket_component(
    component_file=__file__,
    slug="ws-ecc",
    name="WebSocket ECC monitor",
    description="Monitor TX/RX keepalive pulses and timing.",
    router=router,
)
