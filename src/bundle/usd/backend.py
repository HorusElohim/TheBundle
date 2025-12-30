"""Thin adapter over ``pxr.Usd`` so the rest of the app stays backend-agnostic."""

from __future__ import annotations

from typing import Any

from bundle.core import logger

from .model import SceneInfo

LOGGER = logger.get_logger(__name__)


class MissingUSDBackend(RuntimeError):
    """Raised when the pxr USD bindings are unavailable."""


def _require_pxr():
    try:
        from pxr import Usd, UsdGeom  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised via tests
        raise MissingUSDBackend(
            "pxr USD bindings are required to load USD scenes. Install 'usd-core' or 'pxr' to continue."
        ) from exc
    return Usd, UsdGeom


class USDBackend:
    """Minimal USD backend wrapper around pxr calls."""

    def open(self, path: str) -> Any:
        Usd, _ = _require_pxr()
        stage = Usd.Stage.Open(path)
        if stage is None:
            raise FileNotFoundError(f"Unable to open USD stage at {path}")
        LOGGER.debug("Opened USD stage: %s", path)
        return stage

    def save(self, stage_handle: Any) -> None:
        _, _ = _require_pxr()
        root_layer = stage_handle.GetRootLayer()
        root_layer.Save()
        LOGGER.debug("Saved USD stage: %s", root_layer.identifier)

    def stats(self, stage_handle: Any) -> SceneInfo:
        Usd, UsdGeom = _require_pxr()
        prim_count = sum(1 for _ in stage_handle.Traverse())
        layer_count = len(stage_handle.GetLayerStack())
        if hasattr(stage_handle, "GetMetersPerUnit"):
            meters_per_unit = stage_handle.GetMetersPerUnit()
        else:
            # Older USD versions expose this on UsdGeom instead of Stage.
            meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage_handle)
        up_axis = UsdGeom.GetStageUpAxis(stage_handle)
        return SceneInfo(
            prim_count=prim_count,
            layer_count=layer_count,
            meters_per_unit=meters_per_unit,
            up_axis=up_axis,
        )
