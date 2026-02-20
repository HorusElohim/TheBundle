"""Home page routes for the Bundle website."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...core.templating import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "home"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)


router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page with cards for all registered non-home pages."""
    pages_registry = getattr(request.app.state, "pages_registry", [])
    page_cards = [page for page in pages_registry if page.slug != "home" and page.show_on_home]
    context = base_context(request, {"pages": page_cards})
    return templates.TemplateResponse(request, "index.html", context)
