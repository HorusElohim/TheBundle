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
    route_name: str = "static"
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
    template: str | None = None
    assets: list[WidgetAsset] = data.Field(default_factory=list)
    router: APIRouter | None = None
    routers: list[APIRouter] = data.Field(default_factory=list)
    extends: str | None = None
    abstract: bool = False
    ws_path: str | None = None
    name: str | None = None
    description: str | None = None

    @data.model_validator(mode="after")
    def _normalize_routers(self):
        combined: list[APIRouter] = []
        if self.router:
            combined.append(self.router)
        combined.extend(self.routers)

        deduped: list[APIRouter] = []
        seen: set[int] = set()
        for current in combined:
            marker = id(current)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(current)
        self.routers = deduped
        return self


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
    if widget.extends:
        base = _WIDGETS.get(widget.extends)
        if not base:
            raise ValueError(f"Base widget does not exist: {widget.extends}")
        widget = _compose_widget(base, widget)
    _WIDGETS[widget.slug] = widget
    return widget


def widgets(*, include_abstract: bool = False) -> tuple[Widget, ...]:
    _load_builtin_widgets()
    if include_abstract:
        return tuple(_WIDGETS.values())
    return tuple(widget for widget in _WIDGETS.values() if not widget.abstract)


def get(slug: str) -> Widget | None:
    _load_builtin_widgets()
    return _WIDGETS.get(slug)


def _assets_for(items: tuple[Widget, ...]) -> WidgetAssets:
    styles: list[WidgetAsset] = []
    scripts: list[WidgetAsset] = []
    seen: set[tuple[str, str, str, bool]] = set()
    for widget in items:
        for asset in widget.assets:
            key = (asset.kind or "", asset.route_name, asset.path, asset.module)
            if key in seen:
                continue
            seen.add(key)
            if asset.kind == "style":
                styles.append(asset)
            else:
                scripts.append(asset)
    return WidgetAssets(styles=styles, scripts=scripts)


def _compose_widget(base: Widget, child: Widget) -> Widget:
    return Widget(
        slug=child.slug,
        template=child.template or base.template,
        assets=_merge_assets(base.assets, child.assets),
        router=child.router or base.router,
        routers=_merge_routers(base.routers, child.routers),
        extends=child.extends,
        abstract=child.abstract,
        ws_path=child.ws_path or base.ws_path,
        name=child.name or base.name,
        description=child.description or base.description,
    )


def _merge_assets(base_assets: list[WidgetAsset], child_assets: list[WidgetAsset]) -> list[WidgetAsset]:
    merged: list[WidgetAsset] = []
    seen: set[tuple[str, str, str, bool]] = set()
    for asset in [*base_assets, *child_assets]:
        key = (asset.kind or "", asset.route_name, asset.path, asset.module)
        if key in seen:
            continue
        seen.add(key)
        merged.append(asset)
    return merged


def _merge_routers(base_routers: list[APIRouter], child_routers: list[APIRouter]) -> list[APIRouter]:
    merged: list[APIRouter] = []
    seen: set[int] = set()
    for current in [*base_routers, *child_routers]:
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        merged.append(current)
    return merged


def assets() -> WidgetAssets:
    return _assets_for(widgets())


def attach_routes(router: APIRouter) -> None:
    seen: set[int] = set()
    for widget in widgets(include_abstract=True):
        for sub_router in widget.routers:
            marker = id(sub_router)
            if marker in seen:
                continue
            seen.add(marker)
            router.include_router(sub_router)


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
