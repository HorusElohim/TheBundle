from __future__ import annotations

import base64
from enum import Enum
from time import time_ns

from bundle.core import data


class PeerMessageType(str, Enum):
    TEXT = "text"
    FILE = "file"


class PeerMessage(data.Data):
    sender: str = data.Field(default="")
    recipient: str = data.Field(default="")
    timestamp: int = data.Field(default_factory=time_ns)
    type: PeerMessageType = data.Field(default=PeerMessageType.TEXT)

    model_config = data.configuration(extra="allow")


class PeerTextMessage(PeerMessage):
    type: PeerMessageType = data.Field(default=PeerMessageType.TEXT, frozen=True)
    content: str = data.Field(default="")


class PeerFileMessage(PeerMessage):
    type: PeerMessageType = data.Field(default=PeerMessageType.FILE, frozen=True)
    filename: str = data.Field(default="")
    filedata: bytes = data.Field(default=b"")

    # Serialize bytes -> base64 string for JSON safety
    @data.field_serializer("filedata")
    def _ser_filedata(self, value: bytes, info):
        if isinstance(value, (bytes, bytearray)):
            return base64.b64encode(value).decode("ascii")
        return value

    # Accept base64 strings and decode to bytes before validation
    @data.field_validator("filedata", mode="before")
    def _val_filedata(cls, value):
        if isinstance(value, str):
            try:
                return base64.b64decode(value)
            except Exception:
                return value
        return value
