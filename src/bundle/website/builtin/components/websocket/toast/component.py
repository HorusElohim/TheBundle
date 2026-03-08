import time

from fastapi import WebSocket

from bundle.core import tracer

from ..base import WebSocketBaseComponent, WebSocketComponentParams
from ..base.backend import drain_text, every, run_websocket


class WebSocketToastComponent(WebSocketBaseComponent):
    """Websocket component that pushes periodic toast messages to the client."""

    component_file: str = __file__
    slug: str = "ws-toast"
    name: str = "WebSocket Toast Feed"
    description: str = "Toast notifications for incoming messages."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/toast")

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Run periodic server push while draining client messages."""
        await run_websocket(websocket, every(3.0, _send_toast), drain_text)


@tracer.Async.decorator.call_raise
async def _send_toast(websocket: WebSocket) -> None:
    """Send one toast payload."""
    await websocket.send_json({"type": "toast", "body": f"Server ping {int(time.time())}"})
