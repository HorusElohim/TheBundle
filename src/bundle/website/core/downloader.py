# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Downloader adapter that emits progress updates over websocket."""

from __future__ import annotations

from fastapi import WebSocket

from bundle.core import Downloader, data

from .ws_messages import (
    DownloaderEndMessage,
    DownloaderStartMessage,
    DownloaderUpdateMessage,
)


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
