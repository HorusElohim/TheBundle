from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar, Literal

from fastapi import APIRouter

from bundle.core import data

AssetKind = Literal["style", "script"]
COMPONENTS_ROOT = Path(__file__).resolve().parents[1] / "builtin" / "components"
DEFAULT_COMPONENT_ASSET_FILES: tuple[str, ...] = ("component.css", "component.js", "component.mjs")


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
    asset_filenames: ClassVar[tuple[str, ...]] = DEFAULT_COMPONENT_ASSET_FILES
    component_file: str | Path | None = data.Field(default=None, exclude=True, repr=False)

    @data.model_validator(mode="after")
    def _finalize_component(self):
        deduped: list[APIRouter] = []
        seen: set[int] = set()
        for current in self.routers:
            marker = id(current)
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(current)
        self.routers = deduped
        if self.component_file is None:
            return self
        if self.template is None:
            self.template = self.component_template_for(self.component_file)
        if not self.assets:
            self.assets = self.component_assets_for(self.component_file)
        return self

    def build_routers(self) -> list[APIRouter]:
        return self.routers

    @staticmethod
    def component_assets(*paths: str, route_name: str = "components_static") -> list[ComponentAsset]:
        assets: list[ComponentAsset] = []
        for path in paths:
            suffix = Path(path).suffix.lower()
            assets.append(ComponentAsset(path=path, route_name=route_name, module=suffix in {".js", ".mjs"}))
        return assets

    @staticmethod
    def _component_relpath(file_path: Path) -> str:
        return file_path.resolve().relative_to(COMPONENTS_ROOT).as_posix()

    @classmethod
    def component_asset_paths_for(
        cls,
        component_file: str | Path,
        *,
        asset_filenames: Iterable[str] | None = None,
    ) -> list[str]:
        component_dir = Path(component_file).resolve().parent
        names = tuple(asset_filenames) if asset_filenames is not None else cls.asset_filenames
        discovered: list[str] = []
        for asset_name in names:
            asset_path = component_dir / asset_name
            if not asset_path.exists() or not asset_path.is_file():
                continue
            discovered.append(cls._component_relpath(asset_path))
        return discovered

    @classmethod
    def component_assets_for(cls, component_file: str | Path, *, route_name: str = "components_static") -> list[ComponentAsset]:
        return cls.component_assets(*cls.component_asset_paths_for(component_file), route_name=route_name)

    @classmethod
    def component_template_for(cls, component_file: str | Path) -> str | None:
        template_path = Path(component_file).resolve().parent / "template.html"
        if not template_path.exists():
            return None
        return cls._component_relpath(template_path)


class ComponentAssets(data.Data):
    styles: list[ComponentAsset] = data.Field(default_factory=list)
    scripts: list[ComponentAsset] = data.Field(default_factory=list)

    @classmethod
    def from_components(cls, items: tuple[Component, ...]) -> ComponentAssets:
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


__all__ = [
    "COMPONENTS_ROOT",
    "Component",
    "ComponentAsset",
    "ComponentAssets",
    "attach_routes",
    "context",
]
