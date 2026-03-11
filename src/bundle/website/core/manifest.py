"""Site manifest contract for composing website applications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

from fastapi import FastAPI

InitializePages = Callable[[FastAPI], None]


@dataclass(frozen=True)
class SiteManifest:
    """Minimal site contract consumed by the website core app factory."""

    title: str = "Bundle Website"
    static_mount_path: str = "/static"
    components_mount_path: str = "/components-static"
    static_path: Path | None = None
    components_path: Path | None = None
    initialize_pages: InitializePages | None = None
