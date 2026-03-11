"""Reusable page registration primitives for website sites."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles


class Page(Protocol):
    """Structural interface a page module must satisfy to be registered."""

    name: str
    slug: str
    href: str
    description: str
    router: APIRouter
    static_path: Path | None
    show_in_nav: bool
    show_on_home: bool


def mount_page(app: FastAPI, page: Page) -> None:
    """Attach a single page router and its static directory to the app."""
    app.include_router(page.router)
    if page.static_path and page.static_path.is_dir():
        app.mount(
            f"/{page.slug}",
            StaticFiles(directory=str(page.static_path)),
            name=page.slug,
        )


def initialize_pages(app: FastAPI, pages: Iterable[Page]) -> tuple[Page, ...]:
    """Attach all pages and expose registry/navigation metadata on app state."""
    page_registry = tuple(pages)
    for page in page_registry:
        mount_page(app, page)

    app.state.pages_registry = page_registry
    app.state.nav_pages = tuple(page for page in page_registry if page.show_in_nav)
    return page_registry


__all__ = ["Page", "initialize_pages", "mount_page"]
