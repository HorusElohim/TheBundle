from __future__ import annotations

import json
from typing import Awaitable, Callable, Type

from bundle.core import data, logger, sockets

from .message import (
    PeerFileMessage,
    PeerMessage,
    PeerMessageType,
    PeerTextMessage,
)

log = logger.get_logger(__name__)


class MessageCallback(data.Data):
    message_type: PeerMessageType
    callback: Callable[[PeerMessage], Awaitable[None]]

    @property
    def type(self) -> str:
        return self.message_type.value

    async def call(self, message: PeerMessage) -> None:
        if message.type is self.message_type:
            await self.callback(message)


class PeerNode(sockets.Socket):
    """
    Peer node built directly on the ZeroMQ Socket wrapper using PAIR by default.
    Provides typed message send/receive with callback dispatch.
    """

    message_callbacks: dict[str, MessageCallback] = data.Field(default_factory=dict)

    def on(self, msg_type: PeerMessageType, handler: Callable[[PeerMessage], Awaitable[None]]) -> "PeerNode":
        self.message_callbacks[msg_type.value] = MessageCallback(message_type=msg_type, callback=handler)
        return self

    async def send(self, message: PeerMessage) -> None:
        payload = await message.encode()
        await sockets.Socket.send(self, payload)

    async def receive(self) -> bool:
        raw = await sockets.Socket.recv(self)
        raw_dict = json.loads(raw.decode("utf-8"))
        match raw_dict.get("type"):
            case "text":
                msg = await PeerTextMessage.from_dict(raw_dict)
            case "file":
                msg = await PeerFileMessage.from_dict(raw_dict)
            case _:
                log.warning("Unknown message type received: %s", msg.type)
                return False
        if cb := self.message_callbacks.get(msg.type.value):
            await cb.call(msg)
            return True
        log.debug("No callback registered for type=%s", msg.type.value)
        return False

    async def serve(self) -> None:
        while True:
            await self.receive()
