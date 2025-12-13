from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "home"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)


router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sections_registry = getattr(request.app.state, "sections_registry", [])
    section_cards = [section for section in sections_registry if section.slug != "home" and section.show_on_home]
    context = base_context(request, {"sections": section_cards})
    return templates.TemplateResponse("index.html", context)
