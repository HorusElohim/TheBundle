import asyncio
import shutil
import sys
from pathlib import Path

import rich_click as click
import uvicorn

from bundle.core import logger, process, tracer

from . import get_app

log = logger.get_logger(__name__)


def _website_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve_npm_command() -> str | None:
    """Resolve an npm executable name/path, with Windows-safe preference for npm.cmd."""
    candidates = ["npm"]
    if sys.platform.startswith("win"):
        candidates = ["npm.cmd", "npm.exe", "npm"]

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


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


@website.command()
@tracer.Sync.decorator.call_raise
def install():
    """Install website frontend tooling (Node.js/npm on Windows when needed, then npm dependencies)."""
    website_root = _website_root()
    package_json = website_root / "package.json"
    if not package_json.exists():
        raise click.ClickException(
            "package.json not found at website root (src/bundle/website). Initialize frontend tooling first, then run this command."
        )

    runner = process.Process(name="Website.install")
    npm_command = _resolve_npm_command()

    if not npm_command and sys.platform.startswith("win"):
        winget_command = shutil.which("winget.exe") or shutil.which("winget")
        if not winget_command:
            raise click.ClickException(
                "npm is not available on PATH and winget was not found. Install Node.js manually, then rerun `bundle website install`."
            )

        install_node_command = (
            f'"{winget_command}" install -e --id OpenJS.NodeJS.LTS '
            "--accept-source-agreements --accept-package-agreements"
        )
        log.info("npm not found; installing Node.js LTS via winget")
        try:
            asyncio.run(runner(install_node_command, cwd=str(website_root)))
        except process.ProcessError as exc:
            raise click.ClickException(
                f"Node.js installation via winget failed with exit code {exc.result.returncode}."
            ) from exc
        npm_command = _resolve_npm_command()

    if not npm_command:
        raise click.ClickException(
            "npm is not available on PATH. Install Node.js (includes npm), then rerun `bundle website install`."
        )

    npm_install_command = f'"{npm_command}" install'
    log.info(f"installing frontend dependencies: {npm_install_command}")
    try:
        asyncio.run(runner(npm_install_command, cwd=str(website_root)))
    except process.ProcessError as exc:
        raise click.ClickException(f"`npm install` failed with exit code {exc.result.returncode}.") from exc

    log.info("frontend dependencies installed")


@website.command()
@click.option(
    "--script",
    default="build:website-ts",
    show_default=True,
    help="NPM script name to execute for website frontend build.",
)
@tracer.Sync.decorator.call_raise
def build(script: str):
    """Build website frontend assets (for example TypeScript -> JavaScript)."""
    website_root = _website_root()
    package_json = website_root / "package.json"
    if not package_json.exists():
        raise click.ClickException(
            "package.json not found at website root (src/bundle/website). Initialize frontend tooling first, then run this command."
        )

    npm_command = _resolve_npm_command()
    if not npm_command:
        raise click.ClickException(
            "npm is not available on PATH. Install Node.js (includes npm) before running website builds."
        )

    command = f'"{npm_command}" run {script}'
    log.info(f"running frontend build: {command}")
    runner = process.Process(name="Website.build")

    try:
        asyncio.run(runner(command, cwd=str(website_root)))
    except process.ProcessError as exc:
        combined = f"{exc.result.stdout}\n{exc.result.stderr}".lower()
        npm_missing_patterns = [
            "'npm' is not recognized",
            "npm: not found",
            "command not found: npm",
        ]
        if any(pattern in combined for pattern in npm_missing_patterns):
            raise click.ClickException(
                "npm is not available on PATH. Install Node.js (includes npm) before running website builds."
            ) from exc

        tsc_missing_patterns = [
            "'tsc' is not recognized",
            "tsc: not found",
            "command not found: tsc",
        ]
        if any(pattern in combined for pattern in tsc_missing_patterns):
            raise click.ClickException(
                "TypeScript compiler (tsc) is not available. Run `bundle website install`, then retry."
            ) from exc

        raise click.ClickException(f"Frontend build failed with exit code {exc.result.returncode}.") from exc
    log.info("frontend build completed")


if __name__ == "__main__":
    website()
