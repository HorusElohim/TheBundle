from fastapi import FastAPI, HTTPException

from bundle.core.logger import setup_root_logger

WEB_LOGGER = setup_root_logger(__name__, level=10)

app = FastAPI()

from . import common, sections

sections.initialize_sections(app)


@app.exception_handler(404)
async def not_found(request, exc):
    raise HTTPException(404, "Page not found")


WEB_LOGGER.debug("website initialized")
