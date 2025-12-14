from __future__ import annotations

from pathlib import Path

from fastapi import WebSocket

from ...core import Downloader, data
from .websocket import DownloaderEndMessage, DownloaderStartMessage, DownloaderUpdateMessage


class DownloaderWebSocket(Downloader):
    websocket: WebSocket | None = data.Field(default=None, exclude=True)

    async def set_websocket(self, websocket: WebSocket):
        self.websocket = websocket

    async def start(self, byte_size: int):
        """Initializes the download process with the total byte size."""
        if self.websocket:
            await DownloaderStartMessage(total=byte_size).send(self.websocket)

    async def update(self, byte_count: int):
        """Updates the download progress and sends a WebSocket message."""
        if self.websocket:
            await DownloaderUpdateMessage(progress=byte_count).send(self.websocket)

    async def end(self):
        """Finalizes the download process."""
        print("Download completed.")
        # Optionally, send a completion message via WebSocket
        if self.websocket:
            await DownloaderEndMessage().send(self.websocket)


# Usage example (assuming an async context, e.g., an async function):
# downloader = DownloaderWebSocket('wss://your_websocket_server_url')
# await downloader.start(byte_size)
# await downloader.update(byte_count)
# await downloader.end()
