from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import APIRouter

from ... import Component, ComponentAsset, register_component

DEFAULT_WS_PATH = "/ws/ecc"
BASE_COMPONENT_SLUG = "ws-websocket-base"
COMPONENTS_ROOT = Path(__file__).resolve().parents[2]


register_component(
    Component(
        slug=BASE_COMPONENT_SLUG,
        name="WebSocket Component Base",
        description="Shared defaults for websocket-driven components.",
        abstract=True,
        ws_path=DEFAULT_WS_PATH,
    )
)


def websocket_assets(*paths: str, route_name: str = "components_static") -> list[ComponentAsset]:
    assets: list[ComponentAsset] = []
    for path in paths:
        suffix = Path(path).suffix.lower()
        assets.append(ComponentAsset(path=path, route_name=route_name, module=suffix in {".js", ".mjs"}))
    return assets


def _component_relpath(file_path: Path) -> str:
    return file_path.resolve().relative_to(COMPONENTS_ROOT).as_posix()


def component_assets_for(component_file: str | Path, *, route_name: str = "components_static") -> list[ComponentAsset]:
    component_dir = Path(component_file).resolve().parent
    frontend_dir = component_dir / "frontend"
    discovered_paths: list[str] = []
    for asset_name in ("ws.css", "ws.js"):
        asset_path = frontend_dir / asset_name
        if asset_path.exists():
            discovered_paths.append(_component_relpath(asset_path))
    return websocket_assets(*discovered_paths, route_name=route_name)


def component_template_for(component_file: str | Path) -> str | None:
    template_path = Path(component_file).resolve().parent / "template.html"
    if not template_path.exists():
        return None
    return _component_relpath(template_path)


def register_websocket_component(
    *,
    component_file: str | Path,
    slug: str,
    name: str,
    description: str,
    template: str | None = None,
    assets: Iterable[ComponentAsset] | None = None,
    router: APIRouter | None = None,
    ws_path: str | None = None,
    extends: str = BASE_COMPONENT_SLUG,
) -> Component:
    resolved_template = template if template is not None else component_template_for(component_file)
    resolved_assets = list(assets) if assets is not None else component_assets_for(component_file)
    return register_component(
        Component(
            slug=slug,
            name=name,
            description=description,
            template=resolved_template,
            assets=resolved_assets,
            router=router,
            ws_path=ws_path,
            extends=extends,
        )
    )
