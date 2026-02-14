from __future__ import annotations

from pathlib import Path

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
    def component_assets_for(cls, component_file: str | Path, *, route_name: str = "components_static") -> list[ComponentAsset]:
        component_dir = Path(component_file).resolve().parent
        frontend_dir = component_dir / "frontend"
        discovered_paths: list[str] = []
        if frontend_dir.exists():
            for asset_path in sorted(frontend_dir.iterdir()):
                if not asset_path.is_file() or asset_path.suffix.lower() not in {".css", ".js", ".mjs"}:
                    continue
                discovered_paths.append(cls._component_relpath(asset_path))
        return cls.websocket_assets(*discovered_paths, route_name=route_name)

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
