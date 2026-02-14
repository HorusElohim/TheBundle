from __future__ import annotations

from pathlib import Path

from bundle.core import data

from ...component import Component, ComponentAsset

__doc__ = """
Base component abstractions for graphics UI blocks.

The base class auto-discovers template/assets from the component folder and
provides shared typed params for graphics-oriented components.
"""

COMPONENTS_ROOT = Path(__file__).resolve().parents[2]


class GraphicComponentParams(data.Data):
    """Shared parameters for graphics component instances."""

    graph_id: str = "graphics"
    render_mode: str = "base"


class GraphicBaseComponent(Component):
    """Base graphics component with automatic template/assets hydration."""

    component_file: str | Path | None = data.Field(default=None, exclude=True, repr=False)
    params: GraphicComponentParams | None = None

    @data.model_validator(mode="after")
    def _hydrate_graphic_defaults(self):
        if self.params is None:
            self.params = GraphicComponentParams()
        if self.component_file is None:
            return self
        if self.template is None:
            self.template = self.component_template_for(self.component_file)
        if not self.assets:
            self.assets = self.component_assets_for(self.component_file)
        return self

    @staticmethod
    def graphic_assets(*paths: str, route_name: str = "components_static") -> list[ComponentAsset]:
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
        return cls.graphic_assets(*discovered_paths, route_name=route_name)

    @classmethod
    def component_template_for(cls, component_file: str | Path) -> str | None:
        template_path = Path(component_file).resolve().parent / "template.html"
        if not template_path.exists():
            return None
        return cls._component_relpath(template_path)
