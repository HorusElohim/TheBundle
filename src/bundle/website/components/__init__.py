"""Utility components and UI helpers for the Bundle website playground."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter

from bundle.core import data

AssetKind = Literal["style", "script"]


class ComponentAsset(data.Data):
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


class Component(data.Data):
    slug: str
    template: str | None = None
    assets: list[ComponentAsset] = data.Field(default_factory=list)
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


class ComponentAssets(data.Data):
    styles: list[ComponentAsset] = data.Field(default_factory=list)
    scripts: list[ComponentAsset] = data.Field(default_factory=list)


__all__ = [
    "Component",
    "ComponentAsset",
    "ComponentAssets",
    "attach_routes",
    "components",
    "component_assets",
    "context",
    "get_component",
    "register_component",
    "template_context",
]

_COMPONENTS: dict[str, Component] = {}
_COMPONENTS_LOADED = False


def _load_builtin_components() -> None:
    global _COMPONENTS_LOADED
    if _COMPONENTS_LOADED:
        return
    from . import websocket  # noqa: F401

    _COMPONENTS_LOADED = True


def register_component(component: Component) -> Component:
    if component.slug in _COMPONENTS:
        raise ValueError(f"Component already registered: {component.slug}")
    if component.extends:
        base = _COMPONENTS.get(component.extends)
        if not base:
            raise ValueError(f"Base component does not exist: {component.extends}")
        component = _compose_component(base, component)
    _COMPONENTS[component.slug] = component
    return component


def components(*, include_abstract: bool = False) -> tuple[Component, ...]:
    _load_builtin_components()
    if include_abstract:
        return tuple(_COMPONENTS.values())
    return tuple(component for component in _COMPONENTS.values() if not component.abstract)


def get_component(slug: str) -> Component | None:
    _load_builtin_components()
    return _COMPONENTS.get(slug)


def _assets_for(items: tuple[Component, ...]) -> ComponentAssets:
    styles: list[ComponentAsset] = []
    scripts: list[ComponentAsset] = []
    seen: set[tuple[str, str, str, bool]] = set()
    for component in items:
        for asset in component.assets:
            key = (asset.kind or "", asset.route_name, asset.path, asset.module)
            if key in seen:
                continue
            seen.add(key)
            if asset.kind == "style":
                styles.append(asset)
            else:
                scripts.append(asset)
    return ComponentAssets(styles=styles, scripts=scripts)


def _compose_component(base: Component, child: Component) -> Component:
    return Component(
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


def _merge_assets(base_assets: list[ComponentAsset], child_assets: list[ComponentAsset]) -> list[ComponentAsset]:
    merged: list[ComponentAsset] = []
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


def component_assets() -> ComponentAssets:
    return _assets_for(components())


def attach_routes(router: APIRouter) -> None:
    seen: set[int] = set()
    for component in components(include_abstract=True):
        for sub_router in component.routers:
            marker = id(sub_router)
            if marker in seen:
                continue
            seen.add(marker)
            router.include_router(sub_router)


def context(*slugs: str) -> dict[str, Any]:
    if slugs:
        selected_list: list[Component] = []
        for slug in slugs:
            component = get_component(slug)
            if component:
                selected_list.append(component)
        selected = tuple(selected_list)
    else:
        selected = components()
    return {"components": selected, "component_assets": _assets_for(selected)}


def template_context() -> dict[str, Any]:
    return context()
