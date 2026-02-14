from time import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from bundle.core.logger import setup_root_logger

from . import common, sections

WEB_LOGGER = setup_root_logger(__name__, level=10)
STATIC_PATH = common.sections.get_static_path(__file__)
WIDGETS_PATH = Path(__file__).parent / "widgets"


class WidgetStaticFiles(StaticFiles):
    """
    Serve only frontend assets from widget folders.
    Prevent exposing Python sources when mounting the whole widgets tree.
    """

    _ALLOWED_SUFFIXES = {".js", ".mjs", ".css", ".map", ".json", ".png", ".svg", ".woff", ".woff2"}

    async def get_response(self, path: str, scope):  # type: ignore[override]
        # Defensive normalization in case the incoming path still includes query/fragment tokens.
        clean_path = path.split("?", 1)[0].split("#", 1)[0].strip("/")
        rel_path = clean_path.replace("\\", "/")
        normalized_path = "/" + rel_path + "/"
        suffix = Path(rel_path).suffix.lower()
        if "/frontend/" not in normalized_path or suffix not in self._ALLOWED_SUFFIXES:
            return Response(status_code=404)
        return await super().get_response(rel_path, scope)


def get_app() -> FastAPI:
    app = FastAPI(title="Bundle Website")
    app.state.asset_version = str(int(time()))

    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")
    app.mount("/widgets-static", WidgetStaticFiles(directory=str(WIDGETS_PATH)), name="widgets_static")

    # Serve favicon explicitly
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse("static/favicon.ico")

    # Serve site manifest explicitly
    @app.get("/site.webmanifest", include_in_schema=False)
    async def webmanifest():
        return FileResponse("static/site.webmanifest", media_type="application/manifest+json")

    sections.initialize_sections(app)
    return app
