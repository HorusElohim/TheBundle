from __future__ import annotations

import asyncio
import contextlib
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/toast")
async def toast_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    listener_task = asyncio.create_task(_drain_client_messages(websocket))
    try:
        while True:
            await websocket.send_json({"type": "toast", "body": f"Server ping {int(time.time())}"})
            await asyncio.sleep(3.0)
    except (WebSocketDisconnect, RuntimeError):
        return
    finally:
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task


async def _drain_client_messages(websocket: WebSocket) -> None:
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        return
