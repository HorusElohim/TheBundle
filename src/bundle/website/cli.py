import click
import uvicorn


@click.group()
def cli():
    """The Bundle CLI tool."""
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to run the server on.")
@click.option("--port", default=8000, type=int, help="Port to run the server on.")
def start(host, port):
    """Start the FastAPI web server."""
    uvicorn.run("bundle.website:app", host=host, port=port, reload=True, workers=4)


if __name__ == "__main__":
    cli()
