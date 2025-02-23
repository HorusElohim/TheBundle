from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from bundle.core.logger import setup_root_logger

WEB_LOGGER = setup_root_logger(__name__, level=10)


from . import common, sections

STATIC_PATH = common.sections.get_static_path(__file__)


def get_app():
    app = FastAPI()

    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")

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
