"""Excalidraw page route wiring."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from bundle.website.core.templating import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "excalidraw"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


@router.get("/excalidraw", response_class=HTMLResponse)
async def excalidraw_page(request: Request):
    """Render the Excalidraw host page."""
    context = base_context(request, {"title": "Excalidraw"})
    return templates.TemplateResponse(request, "index.html", context)
