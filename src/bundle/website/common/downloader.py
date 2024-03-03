import json

from fastapi import WebSocket

from ...core import Downloader


class DownloaderWebSocket(Downloader):
    async def set_websocket(self, websocket: WebSocket):
        self.websocket = websocket

    async def start(self, byte_size: int):
        """Initializes the download process with the total byte size."""
        await self.websocket.send_text(json.dumps({"type": "downloader_start", "total": byte_size}))

    async def update(self, byte_count: int):
        """Updates the download progress and sends a WebSocket message."""
        await self.websocket.send_text(json.dumps({"type": "downloader_update", "progress": byte_count}))

    async def end(self):
        """Finalizes the download process."""
        print("Download completed.")
        # Optionally, send a completion message via WebSocket
        await self.websocket.send_text(json.dumps({"type": "downloader_end"}))


# Usage example (assuming an async context, e.g., an async function):
# downloader = DownloaderWebSocket('wss://your_websocket_server_url')
# await downloader.start(byte_size)
# await downloader.update(byte_count)
# await downloader.end()
