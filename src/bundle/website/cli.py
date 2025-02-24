import rich_click as click

import uvicorn
from . import get_app


@click.group()
def website():
    """The Bundle CLI tool."""
    pass


@website.command()
@click.option("--host", default="127.0.0.1", help="Host to run the server on.")
@click.option("--port", default=8000, type=int, help="Port to run the server on.")
def start(host, port):
    """Start the FastAPI web server."""
    app = get_app()
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    website()
