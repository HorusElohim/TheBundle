from .. import Widget, WidgetAsset, register

widget = register(
    Widget(
        slug="ws-heartbeat",
        name="WebSocket Heartbeat",
        description="Periodic keepalive loop with a minimal UI.",
        template="widgets/websocket/heartbeat.html",
        assets=[
            WidgetAsset(path="widgets/websocket/heartbeat/ws.css"),
            WidgetAsset(path="widgets/websocket/heartbeat/ws.js", module=True),
        ],
        ws_path="/ws/ecc",
    )
)
