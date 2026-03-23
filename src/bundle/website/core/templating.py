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

"""Template path discovery and shared context helpers for website pages."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

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
_COMPONENT_TEMPLATE_PATH = website_root() / "builtin" / "components"


def create_templates(
    *template_roots: Iterable[Path | str] | Path | str,
) -> Jinja2Templates:
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


class PageModule:
    """Derive page boilerplate (router, templates, logger, paths) from a module file.

    Holds both runtime objects (router, templates, logger) and page metadata
    (name, slug, href, description) so each page declares everything in one place.
    """

    def __init__(
        self,
        module_file: str | Path,
        name: str,
        *,
        slug: str | None = None,
        href: str | None = None,
        description: str = "",
        show_in_nav: bool = True,
        show_on_home: bool = True,
    ) -> None:
        from fastapi import APIRouter

        self.name = name
        self.slug = slug or name.lower().replace(" ", "-")
        self.href = href if href is not None else f"/{self.slug}"
        self.description = description
        self.show_in_nav = show_in_nav
        self.show_on_home = show_on_home
        self.template_path = get_template_path(module_file)
        self.static_path = get_static_path(module_file)
        self.logger = get_logger(self.slug)
        self.router = APIRouter()
        self.templates = create_templates(self.template_path)


__all__ = [
    "PageModule",
    "base_context",
    "create_templates",
    "get_logger",
    "get_static_path",
    "get_template_path",
]
