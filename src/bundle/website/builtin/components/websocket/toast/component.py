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

import time

from fastapi import WebSocket

from bundle.core import tracer

from ..base import WebSocketBaseComponent, WebSocketComponentParams
from ..base.backend import drain_text, every, run_websocket


class WebSocketToastComponent(WebSocketBaseComponent):
    """Websocket component that pushes periodic toast messages to the client."""

    component_file: str = __file__
    slug: str = "ws-toast"
    name: str = "WebSocket Toast Feed"
    description: str = "Toast notifications for incoming messages."
    params: WebSocketComponentParams = WebSocketComponentParams(endpoint="/ws/toast")

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Run periodic server push while draining client messages."""
        await run_websocket(websocket, every(3.0, _send_toast), drain_text)


@tracer.Async.decorator.call_raise
async def _send_toast(websocket: WebSocket) -> None:
    """Send one toast payload."""
    await websocket.send_json({"type": "toast", "body": f"Server ping {int(time.time())}"})
