import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...common.sections import get_logger
from .. import Widget, WidgetAsset, register

LOGGER = get_logger("widgets.ws-ecc")
router = APIRouter()


async def _handle_keepalive(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                await websocket.send_json({"type": "error", "message": "invalid payload"})
                continue
            if payload.get("type") != "keepalive":
                await websocket.send_json({"type": "error", "message": "unknown message"})
                continue
            sent_at = payload.get("sent_at")
            await websocket.send_json(
                {
                    "type": "keepalive_ack",
                    "sent_at": sent_at,
                    "received_at": int(time.time() * 1000),
                }
            )
    except WebSocketDisconnect:
        LOGGER.debug("Playground websocket disconnected")


@router.websocket("/playground/ws/ecc")
async def ecc_websocket(websocket: WebSocket) -> None:
    await _handle_keepalive(websocket)


@router.websocket("/playground/ws")
async def ecc_websocket_legacy(websocket: WebSocket) -> None:
    await _handle_keepalive(websocket)


@router.websocket("/ws/ecc")
async def ecc_websocket_root(websocket: WebSocket) -> None:
    await _handle_keepalive(websocket)


@router.websocket("/ws")
async def ecc_websocket_root_legacy(websocket: WebSocket) -> None:
    await _handle_keepalive(websocket)


widget = register(
    Widget(
        slug="ws-ecc",
        name="WebSocket ECC monitor",
        description="Monitor TX/RX keepalive pulses and timing.",
        template="widgets/websocket/ecc.html",
        assets=[
            WidgetAsset(path="widgets/websocket/ecc/ws.css"),
            WidgetAsset(path="widgets/websocket/ecc/ws.js", module=True),
        ],
        router=router,
        ws_path="/ws/ecc",
    )
)
