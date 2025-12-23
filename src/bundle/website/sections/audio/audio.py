from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ...common.sections import base_context, create_templates, get_logger, get_static_path, get_template_path
from .router import router as audio_router

NAME = "audio"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)

router = APIRouter()
templates = create_templates(TEMPLATE_PATH)
router.include_router(audio_router)


@router.get("/audio", response_class=HTMLResponse)
async def audio_home(request: Request) -> HTMLResponse:
    context = base_context(request, {"ws_endpoint": "/ws/audio"})
    return templates.TemplateResponse(request, "audio.html", context)
