from __future__ import annotations

from bundle.core import data
from bundle.website.core.component import Component

__doc__ = """
Base component abstractions for graphics UI blocks.

The base class auto-discovers template/assets from the component folder and
provides shared typed params for graphics-oriented components.
"""


class GraphicComponentParams(data.Data):
    """Shared parameters for graphics component instances."""

    graph_id: str = "graphics"
    render_mode: str = "base"


class GraphicBaseComponent(Component):
    """Base graphics component with shared typed params."""

    params: GraphicComponentParams = data.Field(default_factory=GraphicComponentParams)
