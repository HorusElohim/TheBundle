from __future__ import annotations

from bundle.core import data

from ..base import GraphicBaseComponent, GraphicComponentParams


class GraphicTwoDComponentParams(GraphicComponentParams):
    """Shared parameters for 2D graphics components."""

    render_mode: str = "2d"
    width: int | None = None
    height: int | None = None
    device_pixel_ratio_cap: float = 2.0

    @data.field_validator("device_pixel_ratio_cap")
    @classmethod
    def _validate_ratio_cap(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("device_pixel_ratio_cap must be greater than 0")
        return value


class GraphicTwoDComponent(GraphicBaseComponent):
    """Base class for canvas/SVG style 2D graphics components."""

    params: GraphicTwoDComponentParams | None = None

    @data.model_validator(mode="after")
    def _ensure_params(self):
        if self.params is None:
            self.params = GraphicTwoDComponentParams()
        elif not isinstance(self.params, GraphicTwoDComponentParams):
            self.params = GraphicTwoDComponentParams(**self.params.model_dump())
        self.params.render_mode = "2d"
        return self
