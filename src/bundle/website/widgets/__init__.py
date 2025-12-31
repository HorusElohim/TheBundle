"""Utility widgets and UI helpers for the Bundle website playground."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter

from bundle.core import data

AssetKind = Literal["style", "script"]


class WidgetAsset(data.Data):
    kind: AssetKind | None = None
    path: str
    module: bool = False

    @data.model_validator(mode="after")
    def _infer_kind(self):
        if self.kind:
            return self
        suffix = Path(self.path).suffix.lower()
        if suffix in {".css"}:
            self.kind = "style"
            return self
        if suffix in {".js", ".mjs"}:
            self.kind = "script"
            return self
        raise ValueError(f"Unsupported asset type for path: {self.path}")


class Widget(data.Data):
    slug: str
    template: str
    assets: list[WidgetAsset] = data.Field(default_factory=list)
    router: APIRouter | None = None
    ws_path: str | None = None
    name: str | None = None
    description: str | None = None


class WidgetAssets(data.Data):
    styles: list[WidgetAsset] = data.Field(default_factory=list)
    scripts: list[WidgetAsset] = data.Field(default_factory=list)


__all__ = [
    "Widget",
    "WidgetAsset",
    "WidgetAssets",
    "attach_routes",
    "assets",
    "context",
    "get",
    "register",
    "template_context",
    "widgets",
]

_WIDGETS: dict[str, Widget] = {}
_WIDGETS_LOADED = False


def _load_builtin_widgets() -> None:
    global _WIDGETS_LOADED
    if _WIDGETS_LOADED:
        return
    from . import websocket  # noqa: F401

    _WIDGETS_LOADED = True


def register(widget: Widget) -> Widget:
    if widget.slug in _WIDGETS:
        raise ValueError(f"Widget already registered: {widget.slug}")
    _WIDGETS[widget.slug] = widget
    return widget


def widgets() -> tuple[Widget, ...]:
    _load_builtin_widgets()
    return tuple(_WIDGETS.values())


def get(slug: str) -> Widget | None:
    _load_builtin_widgets()
    return _WIDGETS.get(slug)


def _assets_for(items: tuple[Widget, ...]) -> WidgetAssets:
    styles: list[WidgetAsset] = []
    scripts: list[WidgetAsset] = []
    seen: set[tuple[str, str, bool]] = set()
    for widget in items:
        for asset in widget.assets:
            key = (asset.kind, asset.path, asset.module)
            if key in seen:
                continue
            seen.add(key)
            if asset.kind == "style":
                styles.append(asset)
            else:
                scripts.append(asset)
    return WidgetAssets(styles=styles, scripts=scripts)


def assets() -> WidgetAssets:
    return _assets_for(widgets())


def attach_routes(router: APIRouter) -> None:
    for widget in widgets():
        if widget.router:
            router.include_router(widget.router)


def context(*slugs: str) -> dict[str, Any]:
    if slugs:
        selected_list: list[Widget] = []
        for slug in slugs:
            widget = get(slug)
            if widget:
                selected_list.append(widget)
        selected = tuple(selected_list)
    else:
        selected = widgets()
    return {"widgets": selected, "widget_assets": _assets_for(selected)}


def template_context() -> dict[str, Any]:
    return context()
