"""Downloader adapter that emits progress updates over websocket."""

from __future__ import annotations

from fastapi import WebSocket

from bundle.core import Downloader, data

from .websocket import DownloaderEndMessage, DownloaderStartMessage, DownloaderUpdateMessage


class DownloaderWebSocket(Downloader):
    """Downloader implementation that streams progress to a websocket client."""

    websocket: WebSocket | None = data.Field(default=None, exclude=True)

    async def set_websocket(self, websocket: WebSocket) -> None:
        """Attach the websocket used for progress event emission."""
        self.websocket = websocket

    async def start(self, byte_size: int) -> None:
        """Emit transfer start with the total expected byte size."""
        if self.websocket:
            await DownloaderStartMessage(total=byte_size).send(self.websocket)

    async def update(self, byte_count: int) -> None:
        """Emit incremental download progress."""
        if self.websocket:
            await DownloaderUpdateMessage(progress=byte_count).send(self.websocket)

    async def end(self) -> None:
        """Emit transfer completion to the websocket progress channel."""
        if self.websocket:
            await DownloaderEndMessage().send(self.websocket)
