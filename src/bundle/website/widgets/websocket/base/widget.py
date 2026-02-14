from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import APIRouter

from ... import Widget, WidgetAsset, register

DEFAULT_WS_PATH = "/ws/ecc"
BASE_WIDGET_SLUG = "ws-websocket-base"


register(
    Widget(
        slug=BASE_WIDGET_SLUG,
        name="WebSocket Widget Base",
        description="Shared defaults for websocket-driven widgets.",
        abstract=True,
        ws_path=DEFAULT_WS_PATH,
    )
)


def websocket_assets(*paths: str, route_name: str = "widgets_static") -> list[WidgetAsset]:
    assets: list[WidgetAsset] = []
    for path in paths:
        suffix = Path(path).suffix.lower()
        assets.append(WidgetAsset(path=path, route_name=route_name, module=suffix in {".js", ".mjs"}))
    return assets


def register_websocket_widget(
    *,
    slug: str,
    name: str,
    description: str,
    template: str,
    assets: Iterable[WidgetAsset],
    router: APIRouter | None = None,
    ws_path: str | None = None,
    extends: str = BASE_WIDGET_SLUG,
) -> Widget:
    return register(
        Widget(
            slug=slug,
            name=name,
            description=description,
            template=template,
            assets=list(assets),
            router=router,
            ws_path=ws_path,
            extends=extends,
        )
    )
