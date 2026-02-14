from ..base.widget import register_websocket_widget, websocket_assets

widget = register_websocket_widget(
    slug="ws-toast",
    name="WebSocket Toast Feed",
    description="Toast notifications for incoming messages.",
    template="websocket/toast/template.html",
    assets=websocket_assets(
        "websocket/toast/frontend/ws.css",
        "websocket/toast/frontend/ws.js",
    ),
)

