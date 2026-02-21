"""Reusable page registration primitives for website sites."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles


@dataclass(frozen=True)
class PageDefinition:
    """Declarative metadata used to register a page router and static mount."""

    name: str
    slug: str
    href: str
    description: str
    router: APIRouter
    static_path: Path
    show_in_nav: bool = True
    show_on_home: bool = True


def mount_page(app: FastAPI, page: PageDefinition) -> None:
    """Attach a single page router and its static directory to the app."""
    app.include_router(page.router)
    app.mount(
        f"/{page.slug}",
        StaticFiles(directory=str(page.static_path)),
        name=page.slug,
    )


def initialize_pages(app: FastAPI, pages: Iterable[PageDefinition]) -> tuple[PageDefinition, ...]:
    """Attach all pages and expose registry/navigation metadata on app state."""
    page_registry = tuple(pages)
    for page in page_registry:
        mount_page(app, page)

    app.state.pages_registry = page_registry
    app.state.nav_pages = tuple(page for page in page_registry if page.show_in_nav)
    return page_registry


__all__ = ["PageDefinition", "mount_page", "initialize_pages"]
