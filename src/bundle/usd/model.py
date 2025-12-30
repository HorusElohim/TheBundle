"""Typed USD protocol models used across CLI, tools, and the website."""

from __future__ import annotations

from typing import Literal

from bundle.core import data


class SceneInfo(data.Data):
    """Metadata describing an opened USD scene."""

    type: Literal["scene_info"] = "scene_info"
    prim_count: int = data.Field(ge=0)
    layer_count: int = data.Field(ge=0)
    meters_per_unit: float | None = data.Field(default=None, gt=0)
    up_axis: str | None = data.Field(default=None)


class LoadScene(data.Data):
    """Command requesting a USD scene to be loaded from disk."""

    type: Literal["load_scene"] = "load_scene"
    path: str = data.Field(min_length=1)


class SceneLoaded(data.Data):
    """Event emitted after a scene has been opened and inspected."""

    type: Literal["scene_loaded"] = "scene_loaded"
    info: SceneInfo


class ErrorEvent(data.Data):
    """Generic error event for transport across websockets or CLIs."""

    type: Literal["error"] = "error"
    message: str
    detail: str | None = None
