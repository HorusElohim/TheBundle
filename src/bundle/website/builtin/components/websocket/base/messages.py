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

from __future__ import annotations

from typing import Literal

from bundle.core import data
from bundle.website.core.ws_messages import WebSocketDataMixin

__doc__ = """
Typed websocket message models built on `bundle.core.data.Data`.

These models provide consistent validation plus async helpers for websocket
serialization/deserialization.
"""


class KeepAliveMessage(data.Data, WebSocketDataMixin):
    """Incoming keepalive ping message."""

    type: Literal["keepalive"] = "keepalive"
    sent_at: int | None = None
    payload: str | None = None


class AckMessage(data.Data, WebSocketDataMixin):
    """Outgoing keepalive acknowledgement."""

    type: Literal["keepalive_ack"] = "keepalive_ack"
    sent_at: int | None = None
    received_at: int
    server_rx_packets: int = 0
    server_tx_packets: int = 0
    server_rx_bytes: int = 0
    server_tx_bytes: int = 0
    request_frame_bytes: int = 0
    request_payload_bytes: int = 0
    ack_frame_bytes: int = 0


class ErrorMessage(data.Data, WebSocketDataMixin):
    """Outgoing protocol error message."""

    type: Literal["error"] = "error"
    message: str
