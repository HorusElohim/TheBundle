import asyncio
import shutil
import sys
from pathlib import Path

import rich_click as click
import uvicorn

from bundle.core import logger, process, tracer

from .core import create_app

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


def _bundle_site_manifest():
    from .sites.thebundle import site_manifest

    return site_manifest()


_SITE_MANIFESTS = {"bundle": _bundle_site_manifest}


@click.group()
@tracer.Sync.decorator.call_raise
async def website():
    """The Bundle CLI tool."""
    pass


@website.group()
@tracer.Sync.decorator.call_raise
def site():
    """Website site commands."""
    pass


@site.command("start")
@click.argument("name", type=click.Choice(tuple(_SITE_MANIFESTS.keys()), case_sensitive=False))
@click.option("--host", default="127.0.0.1", help="Host to run the server on.")
@click.option("--port", default=8000, type=int, help="Port to run the server on.")
@tracer.Sync.decorator.call_raise
def site_start(name: str, host: str, port: int):
    """Start a website site by name."""
    site_name = name.lower()
    log.debug("creating the FastAPI app for site: %s", site_name)
    app = create_app(manifest=_SITE_MANIFESTS[site_name]())
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


@site.command("build")
@click.argument("name", type=click.Choice(tuple(_SITE_MANIFESTS.keys()), case_sensitive=False))
@click.option(
    "--script",
    default="build:website-ts",
    show_default=True,
    help="NPM script name to execute for website frontend build.",
)
@tracer.Sync.decorator.call_raise
def site_build(name: str, script: str):
    """Build website frontend assets for a site (for example TypeScript -> JavaScript)."""
    site_name = name.lower()
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
    log.info("running frontend build for site '%s': %s", site_name, command)
    runner = process.Process(name=f"Website.site_build[{site_name}]")

    try:
        asyncio.run(runner(command, cwd=str(website_root)))
        log.info("frontend build")
    except process.ProcessError as exc:
        log.error("frontend build")
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


if __name__ == "__main__":
    website()
