from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from bundle.core import Data


class AudioSource(Data):
    id: str
    path: str
    sample_rate: int
    channels: int
    duration_sec: float


class AudioView(Data):
    zoom: float
    offset_sec: float
    selection: Optional[Tuple[float, float]]


class AudioTransform(Data):
    type: Literal["gain", "trim", "fade"]
    params: dict


class AudioState(Data):
    source: AudioSource
    view: AudioView
    transforms: List[AudioTransform]
