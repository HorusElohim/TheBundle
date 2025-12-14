from __future__ import annotations

from typing import Literal, Type, TypeVar

from fastapi import WebSocket

from bundle.core import data

MessageT = TypeVar("MessageT", bound=data.Data)


class WebSocketDataMixin:
    async def send(self, websocket: WebSocket) -> None:
        await websocket.send_json(await self.as_dict())

    @classmethod
    async def receive(cls: Type[MessageT], websocket: WebSocket) -> MessageT:
        payload = await websocket.receive_json()
        return await cls.from_dict(payload)


class DownloaderStartMessage(data.Data, WebSocketDataMixin):
    type: Literal["downloader_start"] = "downloader_start"
    total: int = data.Field(ge=0)


class DownloaderUpdateMessage(data.Data, WebSocketDataMixin):
    type: Literal["downloader_update"] = "downloader_update"
    progress: int = data.Field(ge=0)


class DownloaderEndMessage(data.Data, WebSocketDataMixin):
    type: Literal["downloader_end"] = "downloader_end"
