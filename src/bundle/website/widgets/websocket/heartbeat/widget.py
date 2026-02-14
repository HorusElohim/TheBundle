from ..base.widget import register_websocket_widget, websocket_assets

widget = register_websocket_widget(
    slug="ws-heartbeat",
    name="WebSocket Heartbeat",
    description="Periodic keepalive loop with a minimal UI.",
    template="websocket/heartbeat/template.html",
    assets=websocket_assets(
        "websocket/heartbeat/frontend/ws.css",
        "websocket/heartbeat/frontend/ws.js",
    ),
)

