"""Website core app factory and default site bootstrap wiring."""

from __future__ import annotations

from time import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from bundle.core.logger import setup_root_logger

from .manifest import SiteManifest
from .security import SecurityHeadersMiddleware
from .static import ComponentStaticFiles, default_components_path, default_static_path

WEB_LOGGER = setup_root_logger(__name__, level=10)


def _default_manifest() -> SiteManifest:
    """Build the default manifest for the TheBundle site."""
    from ..sites.thebundle import site_manifest

    return site_manifest()


def create_app(manifest: SiteManifest | None = None) -> FastAPI:
    """Create a FastAPI app from the provided site manifest."""
    resolved_manifest = manifest or _default_manifest()
    static_path = resolved_manifest.static_path or default_static_path()
    components_path = resolved_manifest.components_path or default_components_path()

    app = FastAPI(title=resolved_manifest.title)
    app.state.asset_version = str(int(time()))
    app.add_middleware(SecurityHeadersMiddleware)

    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    app.mount("/components-static", ComponentStaticFiles(directory=str(components_path)), name="components_static")

    # Serve favicon explicitly
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Return the favicon asset from the configured static root."""
        return FileResponse(str(static_path / "favicon.ico"))

    # Serve site manifest explicitly
    @app.get("/site.webmanifest", include_in_schema=False)
    async def webmanifest():
        """Return the PWA web manifest from the configured static root."""
        return FileResponse(str(static_path / "site.webmanifest"), media_type="application/manifest+json")

    @app.api_route("/csp-report", methods=["POST", "REPORT"], include_in_schema=False)
    async def csp_report(request: Request):
        """Accept CSP violation reports and log them for inspection."""
        try:
            payload = await request.json()
        except Exception:
            raw = await request.body()
            WEB_LOGGER.warning("CSP report (non-json): %s", raw[:2048].decode("utf-8", errors="replace"))
            return Response(status_code=204)

        reports = []
        if isinstance(payload, list):
            reports = payload
        elif isinstance(payload, dict):
            reports = [payload.get("csp-report", payload)]
        else:
            reports = [payload]

        for report in reports:
            WEB_LOGGER.warning("CSP report: %s", report)
        return Response(status_code=204)

    if resolved_manifest.initialize_pages:
        resolved_manifest.initialize_pages(app)

    return app
