from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...common.sections import get_logger, get_static_path, get_template_path

NAME = "home"
TEMPLATE_PATH = get_template_path(__file__)
STATIC_PATH = get_static_path(__file__)
LOGGER = get_logger(NAME)


router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATE_PATH)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sections": [
                {
                    "name": "BLE",
                    "description": "Scan, inspect, and connect to Nordic UART devices in real time.",
                    "href": "/ble",
                },
                {
                    "name": "YouTube",
                    "description": "Resolve and download tracks directly into The Bundle workbench.",
                    "href": "/youtube",
                },
            ],
        },
    )
