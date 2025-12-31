from .. import Widget, WidgetAsset, register

widget = register(
    Widget(
        slug="ws-toast",
        name="WebSocket Toast Feed",
        description="Toast notifications for incoming messages.",
        template="widgets/websocket/toast.html",
        assets=[
            WidgetAsset(path="widgets/websocket/toast/ws.css"),
            WidgetAsset(path="widgets/websocket/toast/ws.js", module=True),
        ],
        ws_path="/ws/ecc",
    )
)
