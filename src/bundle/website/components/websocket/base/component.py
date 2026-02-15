from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from fastapi import WebSocket

from bundle.core import data

from ...component import Component, ComponentAsset
from .backend import create_router, keepalive_loop

__doc__ = """
Base component abstractions for websocket UI blocks.

The base class auto-discovers template/assets from the component folder and
provides a default keepalive websocket behavior that subclasses can override.
"""

COMPONENTS_ROOT = Path(__file__).resolve().parents[2]


class WebSocketComponentParams(data.Data):
    """Shared websocket parameters for component instances."""

    endpoint: str = "/ws/default"

    @data.field_validator("endpoint")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("WebSocket endpoint path must start with '/'")
        return value

    @property
    def ws_path(self) -> str:
        return self.endpoint


class WebSocketBaseComponent(Component):
    """Base websocket component with automatic template/assets hydration."""

    shared_frontend_assets: ClassVar[tuple[str, ...]] = ("websocket/base/frontend/ws-base.css",)
    component_file: str | Path | None = data.Field(default=None, exclude=True, repr=False)
    params: WebSocketComponentParams | None = None

    @data.model_validator(mode="after")
    def _hydrate_websocket_defaults(self):
        if self.params is None:
            self.params = WebSocketComponentParams()
        if self.component_file is None:
            return self
        if self.template is None:
            self.template = self.component_template_for(self.component_file)
        if not self.assets:
            self.assets = self.component_assets_for(self.component_file)
        return self

    @staticmethod
    def websocket_assets(*paths: str, route_name: str = "components_static") -> list[ComponentAsset]:
        assets: list[ComponentAsset] = []
        for path in paths:
            suffix = Path(path).suffix.lower()
            assets.append(ComponentAsset(path=path, route_name=route_name, module=suffix in {".js", ".mjs"}))
        return assets

    @staticmethod
    def _component_relpath(file_path: Path) -> str:
        return file_path.resolve().relative_to(COMPONENTS_ROOT).as_posix()

    @classmethod
    def _resolve_component_asset(cls, asset_path: str) -> str | None:
        candidate = (COMPONENTS_ROOT / asset_path).resolve()
        try:
            return cls._component_relpath(candidate)
        except ValueError:
            return None

    @classmethod
    def shared_asset_paths(cls) -> list[str]:
        paths: list[str] = []
        for asset_name in cls.shared_frontend_assets:
            resolved = cls._resolve_component_asset(asset_name)
            if resolved is None:
                continue
            if (COMPONENTS_ROOT / resolved).exists():
                paths.append(resolved)
        return paths

    @classmethod
    def component_assets_for(cls, component_file: str | Path, *, route_name: str = "components_static") -> list[ComponentAsset]:
        component_dir = Path(component_file).resolve().parent
        frontend_dir = component_dir / "frontend"
        discovered_paths: list[str] = cls.shared_asset_paths()
        if frontend_dir.exists():
            for asset_path in sorted(frontend_dir.iterdir()):
                if not asset_path.is_file() or asset_path.suffix.lower() not in {".css", ".js", ".mjs"}:
                    continue
                discovered_paths.append(cls._component_relpath(asset_path))
        unique_paths = list(dict.fromkeys(discovered_paths))
        return cls.websocket_assets(*unique_paths, route_name=route_name)

    @classmethod
    def component_template_for(cls, component_file: str | Path) -> str | None:
        template_path = Path(component_file).resolve().parent / "template.html"
        if not template_path.exists():
            return None
        return cls._component_relpath(template_path)

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Default websocket handler (keepalive protocol)."""
        await keepalive_loop(websocket)

    def build_routers(self):
        """Attach the component websocket route using the configured endpoint."""
        return [create_router(self.params.endpoint, self.handle_websocket)]
