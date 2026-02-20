"""Page registry and mount orchestration for the default Bundle website."""

from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles

from ..core.templating import get_logger
from . import ble
from . import excalibur as excalidraw
from . import home, playground, youtube

LOGGER = get_logger("pages")


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


PAGE_REGISTRY: tuple[PageDefinition, ...] = (
    PageDefinition(
        name="Home",
        slug="home",
        href="/",
        description="Choose a lab to explore.",
        router=home.router,
        static_path=home.STATIC_PATH,
    ),
    PageDefinition(
        name="BLE",
        slug="ble",
        href="/ble",
        description="Scan, inspect, and connect to Nordic UART devices in real time.",
        router=ble.router,
        static_path=ble.STATIC_PATH,
    ),
    PageDefinition(
        name="YouTube",
        slug="youtube",
        href="/youtube",
        description="Resolve and download tracks directly into The Bundle workbench.",
        router=youtube.router,
        static_path=youtube.STATIC_PATH,
    ),
    PageDefinition(
        name="Excalidraw",
        slug="excalidraw",
        href="/excalidraw",
        description="Draw and brainstorm with the Excalidraw canvas.",
        router=excalidraw.router,
        static_path=excalidraw.STATIC_PATH,
    ),
    PageDefinition(
        name="Playground",
        slug="playground",
        href="/playground",
        description="Prototype components quickly with backend and frontend hooks.",
        router=playground.router,
        static_path=playground.STATIC_PATH,
    ),
)


def mount_page(app: FastAPI, page: PageDefinition) -> None:
    """Attach a single page router and its static directory to the app."""
    token = f"*({page.slug})"
    LOGGER.debug("%s registering page..", token)
    LOGGER.debug("%s router", token)
    app.include_router(page.router)
    LOGGER.debug("%s static: %s", token, page.static_path)
    app.mount(
        f"/{page.slug}",
        StaticFiles(directory=str(page.static_path)),
        name=page.slug,
    )
    LOGGER.debug("%s registered", token)


def initialize_pages(app: FastAPI) -> None:
    """Attach all pages and expose registry/navigation metadata on app state."""
    for page in PAGE_REGISTRY:
        mount_page(app, page)

    app.state.pages_registry = PAGE_REGISTRY
    app.state.nav_pages = tuple(page for page in PAGE_REGISTRY if page.show_in_nav)
