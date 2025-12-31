from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ... import widgets
from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "playground"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)
widgets.attach_routes(router)


@router.get("/playground", response_class=HTMLResponse)
async def playground(request: Request):
    LOGGER.debug("Rendering playground page")
    context = base_context(request, widgets.context("ws-ecc", "ws-heartbeat", "ws-toast"))
    return templates.TemplateResponse(request, "playground.html", context)
