import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ....common.pages import get_logger

LOGGER = get_logger("components.ws-ecc")
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
