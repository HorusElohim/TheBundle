"""Template path discovery and shared context helpers for website pages."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

from fastapi.templating import Jinja2Templates

from .static import website_root


def get_template_path(file_path: str | Path) -> Path:
    """Resolve the page-local template folder for the given module file."""
    return Path(file_path).parent / "templates"


def get_static_path(file_path: str | Path) -> Path:
    """Resolve the page-local static folder for the given module file."""
    return Path(file_path).parent / "static"


def get_logger(page_name: str) -> logging.Logger:
    """Return a namespaced logger for website page/component modules."""
    return logging.getLogger(f"bundle.website.{page_name}")


_BASE_TEMPLATE_PATH = website_root() / "templates"
_COMPONENT_TEMPLATE_PATH = website_root() / "builtin" / "component"


def create_templates(*template_roots: Iterable[Path | str] | Path | str) -> Jinja2Templates:
    """
    Create a Jinja environment that can resolve page templates and shared layouts.

    The shared base template and component template roots are always appended.
    """
    paths: list[Path] = []
    for root in template_roots:
        if isinstance(root, (str, Path)):
            paths.append(Path(root))
        else:
            paths.extend(Path(p) for p in root)
    paths.append(_BASE_TEMPLATE_PATH)
    paths.append(_COMPONENT_TEMPLATE_PATH)
    search_paths = [str(path) for path in paths]
    return Jinja2Templates(directory=search_paths)


def base_context(request: Any, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the shared template context for website pages."""
    extra = extra or {}
    app_state = getattr(getattr(request, "app", None), "state", None)
    nav_pages = getattr(app_state, "nav_pages", [])
    asset_version = getattr(app_state, "asset_version", "dev")
    static_mount_path = getattr(app_state, "static_mount_path", "/static")
    components_mount_path = getattr(app_state, "components_mount_path", "/components-static")
    website_runtime = {
        "mounts": {
            "static": static_mount_path,
            "components": components_mount_path,
        },
        "assetVersion": str(asset_version),
    }
    return {
        "request": request,
        "nav_pages": nav_pages,
        "asset_version": asset_version,
        "website_runtime": website_runtime,
        **extra,
    }


__all__ = [
    "get_template_path",
    "get_static_path",
    "get_logger",
    "create_templates",
    "base_context",
]
