from __future__ import annotations

import time

from fastapi import WebSocket, WebSocketDisconnect


async def keepalive_loop(websocket: WebSocket) -> None:
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
        return
