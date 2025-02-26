import rich_click as click
import uvicorn

from bundle.core import logger, tracer

from . import get_app

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def website():
    """The Bundle CLI tool."""
    pass


@website.command()
@click.option("--host", default="127.0.0.1", help="Host to run the server on.")
@click.option("--port", default=8000, type=int, help="Port to run the server on.")
@tracer.Sync.decorator.call_raise
def start(host, port):
    """Start the FastAPI web server."""
    log.debug("creating the FastAPI app")
    app = get_app()
    log.info(f"running on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    website()
