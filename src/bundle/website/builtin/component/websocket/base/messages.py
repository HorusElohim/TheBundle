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
