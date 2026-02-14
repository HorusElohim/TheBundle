from __future__ import annotations

from bundle.core import data

from ..base import GraphicBaseComponent, GraphicComponentParams


class GraphicThreeDComponentParams(GraphicComponentParams):
    """Shared parameters for 3D graphics components."""

    render_mode: str = "3d"
    camera_mode: str = "orbit"
    field_of_view: float = 40.0
    near: float = 0.1
    far: float = 100.0

    @data.model_validator(mode="after")
    def _validate_camera_clip(self):
        if self.field_of_view <= 0:
            raise ValueError("field_of_view must be greater than 0")
        if self.near <= 0:
            raise ValueError("near clip distance must be greater than 0")
        if self.far <= self.near:
            raise ValueError("far clip distance must be greater than near clip distance")
        return self


class GraphicThreeDComponent(GraphicBaseComponent):
    """Base class for Three.js/WebGL style 3D graphics components."""

    params: GraphicThreeDComponentParams | None = None

    @data.model_validator(mode="after")
    def _ensure_params(self):
        if self.params is None:
            self.params = GraphicThreeDComponentParams()
        elif not isinstance(self.params, GraphicThreeDComponentParams):
            self.params = GraphicThreeDComponentParams(**self.params.model_dump())
        self.params.render_mode = "3d"
        return self
