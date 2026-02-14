from __future__ import annotations

from fastapi import APIRouter, WebSocket

from ..base import keepalive_loop

router = APIRouter()


@router.websocket("/ws/heartbeat")
async def heartbeat_websocket(websocket: WebSocket) -> None:
    await keepalive_loop(websocket)
