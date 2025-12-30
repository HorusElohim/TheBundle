from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path

NAME = "usd"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)


@router.get("/usd", response_class=HTMLResponse)
async def usd(request: Request):
    context = base_context(request)
    return templates.TemplateResponse(request, "usd.html", context)


from . import ws  # noqa: E402  # isort:skip
