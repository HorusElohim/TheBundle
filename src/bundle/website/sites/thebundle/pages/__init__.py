"""Page registry for the TheBundle site."""

from __future__ import annotations

from fastapi import FastAPI

from ....core.pages import PageDefinition, initialize_pages as initialize_site_pages
from .ble import page as ble_page
from .excalidraw import page as excalidraw_page
from .home import page as home_page
from .playground import page as playground_page
from .youtube import page as youtube_page

PAGE_REGISTRY: tuple[PageDefinition, ...] = (
    PageDefinition(
        name="Home",
        slug="home",
        href="/",
        description="Choose a lab to explore.",
        router=home_page.router,
        static_path=home_page.STATIC_PATH,
    ),
    PageDefinition(
        name="BLE",
        slug="ble",
        href="/ble",
        description="Scan, inspect, and connect to Nordic UART devices in real time.",
        router=ble_page.router,
        static_path=ble_page.STATIC_PATH,
    ),
    PageDefinition(
        name="YouTube",
        slug="youtube",
        href="/youtube",
        description="Resolve and download tracks directly into The Bundle workbench.",
        router=youtube_page.router,
        static_path=youtube_page.STATIC_PATH,
    ),
    PageDefinition(
        name="Excalidraw",
        slug="excalidraw",
        href="/excalidraw",
        description="Draw and brainstorm with the Excalidraw canvas.",
        router=excalidraw_page.router,
        static_path=excalidraw_page.STATIC_PATH,
    ),
    PageDefinition(
        name="Playground",
        slug="playground",
        href="/playground",
        description="Prototype components quickly with backend and frontend hooks.",
        router=playground_page.router,
        static_path=playground_page.STATIC_PATH,
    ),
)


def initialize_pages(app: FastAPI) -> None:
    """Attach all TheBundle pages and publish navigation metadata on app state."""
    initialize_site_pages(app, PAGE_REGISTRY)
