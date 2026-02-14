from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bundle.core import tracer

from .message_router import MessageRouter
from .messages import AckMessage, ErrorMessage, KeepAliveMessage

__doc__ = """
Composable websocket backend helpers for website components.

This module provides small building blocks to define websocket behavior:
- route creation (`create_router`)
- shared lifecycle with task cancellation (`run_websocket`)
- loop primitives (`every`, `drain_text`, `receive_json`)
- typed payload dispatch (`message_router.MessageRouter`)
- default keepalive protocol (`keepalive_loop`)
"""


WebSocketHandler = Callable[[WebSocket], Awaitable[None]]
TaskFactory = Callable[[WebSocket], Awaitable[None]]


def create_router(endpoint: str, handler: WebSocketHandler | None = None) -> APIRouter:
    """
    Build a websocket router bound to `endpoint`.

    Args:
        endpoint: FastAPI websocket path (for example `/ws/ecc`).
        handler: Websocket coroutine handler. Defaults to `keepalive_loop`.

    Returns:
        APIRouter with one websocket entrypoint.
    """
    router = APIRouter()
    resolved_handler = handler or keepalive_loop

    @router.websocket(endpoint)
    async def ecc_websocket(websocket: WebSocket) -> None:
        await resolved_handler(websocket)

    return router


async def run_websocket(websocket: WebSocket, *task_factories: TaskFactory) -> None:
    """
    Run one websocket session with composable async tasks.

    The function accepts the connection, starts all tasks, waits for completion,
    and performs robust cancellation cleanup when the socket closes.
    """
    await websocket.accept()
    tasks = [asyncio.create_task(factory(websocket)) for factory in task_factories]
    try:
        if tasks:
            await asyncio.gather(*tasks)
    except (WebSocketDisconnect, RuntimeError):
        return
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                await task


def every(seconds: float, tick: TaskFactory) -> TaskFactory:
    """Return a task factory that runs `tick` periodically every `seconds`."""

    async def _runner(websocket: WebSocket) -> None:
        while True:
            await tick(websocket)
            await asyncio.sleep(seconds)

    return _runner


async def drain_text(websocket: WebSocket) -> None:
    """Consume and discard incoming text frames until disconnect."""
    while True:
        await websocket.receive_text()


def receive_json(handle: Callable[[WebSocket, dict], Awaitable[None]]) -> TaskFactory:
    """Return a task factory that reads JSON objects and forwards them to `handle`."""

    async def _runner(websocket: WebSocket) -> None:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                await ErrorMessage(message="invalid payload").send(websocket)
                continue
            await handle(websocket, payload)

    return _runner


async def keepalive_loop(websocket: WebSocket) -> None:
    """Default keepalive protocol: `keepalive` -> `keepalive_ack`."""

    @tracer.Async.decorator.call_raise
    async def _on_keepalive(ws: WebSocket, message: KeepAliveMessage) -> None:
        await AckMessage(sent_at=message.sent_at, received_at=int(time.time() * 1000)).send(ws)

    router = MessageRouter().on(KeepAliveMessage, _on_keepalive)
    await run_websocket(websocket, receive_json(router.dispatch))
