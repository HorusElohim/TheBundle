from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import WebSocket

from bundle.core import data

from .messages import ErrorMessage

MessageT = TypeVar("MessageT", bound=data.Data)


class MessageRouter:
    """Typed dispatcher that routes websocket payloads by their `type` field."""

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[type[data.Data], Callable[[WebSocket, data.Data], Awaitable[None]]]] = {}

    def on(
        self,
        message_type: type[MessageT],
        handler: Callable[[WebSocket, MessageT], Awaitable[None]],
    ) -> MessageRouter:
        """Register a callback for a `Data` message model."""
        kind = message_type.model_fields["type"].default
        if not isinstance(kind, str) or not kind:
            raise ValueError(f"Message type {message_type.__name__} must define a default 'type' string")
        self._handlers[kind] = (message_type, handler)
        return self

    async def dispatch(self, websocket: WebSocket, payload: dict) -> None:
        """Deserialize payload and execute the registered typed callback."""
        raw_type = payload.get("type")
        entry = self._handlers.get(raw_type)
        if entry is None:
            await ErrorMessage(message="unknown message").send(websocket)
            return
        model_cls, handler = entry
        try:
            message = await model_cls.from_dict(payload)
        except Exception:
            await ErrorMessage(message="invalid payload").send(websocket)
            return
        await handler(websocket, message)
