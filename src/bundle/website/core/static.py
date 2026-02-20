"""Static path helpers and guarded component static file serving."""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles


def website_root() -> Path:
    """Return the website package root directory."""
    return Path(__file__).resolve().parents[1]


def default_static_path() -> Path:
    """Return the default global static directory for the website app."""
    return website_root() / "static"


def default_components_path() -> Path:
    """Return the default components root directory for static mounting."""
    return website_root() / "components"


class ComponentStaticFiles(StaticFiles):
    """
    Serve only safe static asset types from component folders.

    The allowlist blocks Python/templates and only exposes frontend-oriented
    asset types. This supports both current `frontend/...` layouts and the
    future atomic component layout (`component.ts` / `component.css` in root).
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
        suffix = Path(rel_path).suffix.lower()
        if suffix not in self._ALLOWED_SUFFIXES:
            return Response(status_code=404)
        return await super().get_response(rel_path, scope)
