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
    routers: list[APIRouter] = data.Field(default_factory=list)
    params: data.Data | None = None
    name: str | None = None
    description: str | None = None

    @data.model_validator(mode="after")
    def _normalize_routers(self):
        deduped: list[APIRouter] = []
        seen: set[int] = set()
        for current in self.routers:
            marker = id(current)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(current)
        self.routers = deduped
        return self

    def build_routers(self) -> list[APIRouter]:
        return self.routers


class ComponentAssets(data.Data):
    styles: list[ComponentAsset] = data.Field(default_factory=list)
    scripts: list[ComponentAsset] = data.Field(default_factory=list)

    @classmethod
    def from_components(cls, items: tuple[Component, ...]) -> "ComponentAssets":
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
        return cls(styles=styles, scripts=scripts)


__all__ = [
    "Component",
    "ComponentAsset",
    "ComponentAssets",
    "attach_routes",
    "context",
]


def attach_routes(router: APIRouter, *items: Component) -> None:
    seen: set[int] = set()
    for component in items:
        for sub_router in component.build_routers():
            marker = id(sub_router)
            if marker in seen:
                continue
            seen.add(marker)
            router.include_router(sub_router)


def context(*items: Component) -> dict[str, Any]:
    selected = tuple(items)
    return {"components": selected, "component_assets": ComponentAssets.from_components(selected)}
