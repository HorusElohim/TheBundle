from __future__ import annotations

from enum import Enum
from typing import Any

from bundle.core import Data

PROTOCOL_VERSION = 1


class AudioMessageType(str, Enum):
    LOAD = "audio.load"
    VIEW_SET = "audio.view.set"
    SELECT = "audio.select"
    TRANSFORM_ADD = "audio.transform.add"
    TRANSFORM_CLEAR = "audio.transform.clear"
    STATE = "audio.state"
    WAVEFORM_CHUNK = "audio.waveform.chunk"
    ERROR = "audio.error"


class MessageEnvelope(Data):
    v: int
    type: AudioMessageType
    payload: dict[str, Any]


class AudioLoad(Data):
    type: AudioMessageType = AudioMessageType.LOAD
    path: str


class AudioViewSet(Data):
    type: AudioMessageType = AudioMessageType.VIEW_SET
    zoom: float
    offset_sec: float


class AudioSelect(Data):
    type: AudioMessageType = AudioMessageType.SELECT
    start: float
    end: float


class AudioTransformAdd(Data):
    type: AudioMessageType = AudioMessageType.TRANSFORM_ADD
    transform: dict[str, Any]


class AudioTransformClear(Data):
    type: AudioMessageType = AudioMessageType.TRANSFORM_CLEAR


IncomingMessage = AudioLoad | AudioViewSet | AudioSelect | AudioTransformAdd | AudioTransformClear


def build_envelope(message_type: AudioMessageType | str, payload: dict[str, Any]) -> dict[str, Any]:
    message_value = message_type.value if isinstance(message_type, AudioMessageType) else message_type
    return {"v": PROTOCOL_VERSION, "type": message_value, "payload": payload}
