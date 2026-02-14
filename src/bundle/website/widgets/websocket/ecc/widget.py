from ..base.widget import register_websocket_widget, websocket_assets
from .backend import router

widget = register_websocket_widget(
    slug="ws-ecc",
    name="WebSocket ECC monitor",
    description="Monitor TX/RX keepalive pulses and timing.",
    template="websocket/ecc/template.html",
    assets=websocket_assets(
        "websocket/ecc/frontend/ws.css",
        "websocket/ecc/frontend/ws.js",
    ),
    router=router,
)

