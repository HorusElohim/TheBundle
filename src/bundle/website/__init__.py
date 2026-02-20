from time import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from bundle.core.logger import setup_root_logger

from . import common, pages

WEB_LOGGER = setup_root_logger(__name__, level=10)
STATIC_PATH = common.pages.get_static_path(__file__)
COMPONENTS_PATH = Path(__file__).parent / "components"

DEFAULT_CSP = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'self'",
        "frame-src 'self'",
        "img-src 'self' data: blob: https://*.ytimg.com https://ytimg.com",
        "font-src 'self' data:",
        "style-src 'self'",
        "script-src 'self' https://unpkg.com https://esm.sh 'report-sample'",
        "worker-src 'self'",
        "connect-src 'self' ws: wss: https://esm.sh",
        "report-uri /csp-report",
    ]
)

EXCALIDRAW_CSP = "; ".join(
    [
        "default-src 'self' https://excalidraw.nyc3.cdn.digitaloceanspaces.com",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'self'",
        "frame-src 'self'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data: https:",
        "style-src 'self' 'unsafe-inline' https:",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://scripts.simpleanalyticscdn.com https://excalidraw.nyc3.cdn.digitaloceanspaces.com https://esm.sh 'report-sample'",
        "worker-src 'self' blob:",
        "connect-src 'self' ws: wss: https: https://esm.sh",
        "report-uri /csp-report",
    ]
)


class ComponentStaticFiles(StaticFiles):
    """
    Serve only frontend assets from component folders.
    Prevent exposing Python sources when mounting the whole components tree.
    """

    _ALLOWED_SUFFIXES = {
        ".js",
        ".mjs",
        ".css",
        ".map",
        ".json",
        ".png",
        ".jpg",
        ".jpeg",
        ".hdr",
        ".svg",
        ".woff",
        ".woff2",
    }

    async def get_response(self, path: str, scope):  # type: ignore[override]
        # Defensive normalization in case the incoming path still includes query/fragment tokens.
        clean_path = path.split("?", 1)[0].split("#", 1)[0].strip("/")
        rel_path = clean_path.replace("\\", "/")
        normalized_path = "/" + rel_path + "/"
        suffix = Path(rel_path).suffix.lower()
        if "/frontend/" not in normalized_path or suffix not in self._ALLOWED_SUFFIXES:
            return Response(status_code=404)
        return await super().get_response(rel_path, scope)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply per-route CSP to keep pages isolated and avoid script leakage."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        is_excalidraw = path.startswith("/excalidraw")
        selected_csp = EXCALIDRAW_CSP if is_excalidraw else DEFAULT_CSP
        response.headers["Content-Security-Policy"] = selected_csp
        response.headers["Content-Security-Policy-Report-Only"] = selected_csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def get_app() -> FastAPI:
    app = FastAPI(title="Bundle Website")
    app.state.asset_version = str(int(time()))
    app.add_middleware(SecurityHeadersMiddleware)

    app.mount("/static", StaticFiles(directory=str(STATIC_PATH)), name="static")
    app.mount("/components-static", ComponentStaticFiles(directory=str(COMPONENTS_PATH)), name="components_static")

    # Serve favicon explicitly
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse("static/favicon.ico")

    # Serve site manifest explicitly
    @app.get("/site.webmanifest", include_in_schema=False)
    async def webmanifest():
        return FileResponse("static/site.webmanifest", media_type="application/manifest+json")

    @app.api_route("/csp-report", methods=["POST", "REPORT"], include_in_schema=False)
    async def csp_report(request: Request):
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

    pages.initialize_pages(app)
    return app
