"""Playground page showcasing reusable website components."""

from inspect import getfile

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from bundle.website.core import components
from bundle.website.core.templating import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "playground"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


COMPONENTS = (
    components.graphic.GraphicTwoDComponent(
        slug="graphic-2d",
        name="Graphic 2D",
        description="Interactive particle network rendered on a 2D canvas.",
        component_file=getfile(components.graphic.GraphicTwoDComponent),
    ),
    components.graphic.GraphicThreeDComponent(
        slug="graphic-3d",
        name="Graphic 3D",
        description="Pseudo-3D starfield with pointer-driven parallax.",
        component_file=getfile(components.graphic.GraphicThreeDComponent),
    ),
    components.WebSocketECCComponent(params=components.WebSocketComponentParams(endpoint="/ws/ecc-1")),
    components.WebSocketECCComponent(params=components.WebSocketComponentParams(endpoint="/ws/ecc-2")),
    components.WebSocketHeartbeatComponent(),
    components.WebSocketHeartBeatCardioComponent(),
    components.WebSocketHeartBeatMonitorEarthComponent(),
    components.WebSocketHeartBeatMonitorEarthMoonComponent(),
    components.WebSocketToastComponent(),
)

components.attach_routes(router, *COMPONENTS)


@router.get("/playground", response_class=HTMLResponse)
async def playground(request: Request):
    """Render the playground with all demo components and their assets."""
    LOGGER.debug("Rendering playground page")
    context = base_context(request, components.context(*COMPONENTS))
    return templates.TemplateResponse(request, "playground.html", context)
