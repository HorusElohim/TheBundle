from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ... import components
from ...common.pages import base_context, create_templates, get_logger, get_static_path, get_template_path
from ...components.websocket.base import WebSocketComponentParams
from ...components.websocket import ecc, heartbeat, heartbeat_earth, toast

NAME = "playground"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


COMPONENTS = (
    ecc.WebSocketECCComponent(params=WebSocketComponentParams(endpoint="/ws/ecc-1")),
    ecc.WebSocketECCComponent(params=WebSocketComponentParams(endpoint="/ws/ecc-2")),
    heartbeat.WebSocketHeartbeatComponent(),
    heartbeat_earth.WebSocketHeartBeatMonitorEarthComponent(),
    toast.WebSocketToastComponent(),
)

components.attach_routes(router, *COMPONENTS)


@router.get("/playground", response_class=HTMLResponse)
async def playground(request: Request):
    LOGGER.debug("Rendering playground page")
    context = base_context(request, components.context(*COMPONENTS))
    return templates.TemplateResponse(request, "playground.html", context)
