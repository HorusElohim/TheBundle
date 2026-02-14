from __future__ import annotations

from typing import Literal, TypeVar

from fastapi import WebSocket

from bundle.core import data

__doc__ = """
Typed websocket message models built on `bundle.core.data.Data`.

These models provide consistent validation plus async helpers for websocket
serialization/deserialization.
"""

MessageT = TypeVar("MessageT", bound=data.Data)


class WebSocketDataMixin:
    """Mixin that adds websocket send/receive helpers to `Data` messages."""

    async def send(self, websocket: WebSocket) -> None:
        """Serialize the current message and send it over websocket."""
        await websocket.send_json(await self.as_dict())

    @classmethod
    async def receive(cls: type[MessageT], websocket: WebSocket) -> MessageT:
        """Receive JSON from websocket and deserialize as `cls`."""
        payload = await websocket.receive_json()
        return await cls.from_dict(payload)


class KeepAliveMessage(data.Data, WebSocketDataMixin):
    """Incoming keepalive ping message."""

    type: Literal["keepalive"] = "keepalive"
    sent_at: int | None = None


class AckMessage(data.Data, WebSocketDataMixin):
    """Outgoing keepalive acknowledgement."""

    type: Literal["keepalive_ack"] = "keepalive_ack"
    sent_at: int | None = None
    received_at: int


class ErrorMessage(data.Data, WebSocketDataMixin):
    """Outgoing protocol error message."""

    type: Literal["error"] = "error"
    message: str
