from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "excalidraw"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


@router.get("/excalidraw", response_class=HTMLResponse)
async def excalidraw_page(request: Request):
    context = base_context(request, {"title": "Excalidraw"})
    return templates.TemplateResponse("index.html", context)
