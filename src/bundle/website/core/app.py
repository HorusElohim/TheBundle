# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

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


def _normalize_mount_path(path: str, *, field_name: str) -> str:
    normalized = (path or "").strip()
    if not normalized.startswith("/"):
        raise ValueError(f"{field_name} must start with '/'")
    if len(normalized) > 1:
        normalized = normalized.rstrip("/")
    if normalized == "/":
        raise ValueError(f"{field_name} cannot be '/'")
    return normalized


def create_app(manifest: SiteManifest | None = None) -> FastAPI:
    """Create a FastAPI app from the provided site manifest."""
    resolved_manifest = manifest or _default_manifest()
    static_path = resolved_manifest.static_path or default_static_path()
    components_path = resolved_manifest.components_path or default_components_path()
    static_mount_path = _normalize_mount_path(
        resolved_manifest.static_mount_path,
        field_name="SiteManifest.static_mount_path",
    )
    components_mount_path = _normalize_mount_path(
        resolved_manifest.components_mount_path,
        field_name="SiteManifest.components_mount_path",
    )

    app = FastAPI(title=resolved_manifest.title)
    app.state.asset_version = str(int(time()))
    app.state.static_mount_path = static_mount_path
    app.state.components_mount_path = components_mount_path
    app.add_middleware(SecurityHeadersMiddleware)

    app.mount(static_mount_path, StaticFiles(directory=str(static_path)), name="static")
    app.mount(
        components_mount_path,
        ComponentStaticFiles(directory=str(components_path)),
        name="components_static",
    )

    # Serve favicon explicitly
    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Return the favicon asset from the configured static root."""
        return FileResponse(str(static_path / "favicon.ico"))

    # Serve site manifest explicitly
    @app.get("/site.webmanifest", include_in_schema=False)
    async def webmanifest():
        """Return the PWA web manifest from the configured static root."""
        return FileResponse(
            str(static_path / "site.webmanifest"),
            media_type="application/manifest+json",
        )

    @app.api_route("/csp-report", methods=["POST", "REPORT"], include_in_schema=False)
    async def csp_report(request: Request):
        """Accept CSP violation reports and log them for inspection."""
        try:
            payload = await request.json()
        except Exception:
            raw = await request.body()
            WEB_LOGGER.warning(
                "CSP report (non-json): %s",
                raw[:2048].decode("utf-8", errors="replace"),
            )
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
