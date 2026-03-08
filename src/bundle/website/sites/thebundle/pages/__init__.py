"""Page registry for the TheBundle site."""

from __future__ import annotations

from fastapi import FastAPI

from ....core.pages import initialize_pages as initialize_site_pages
from . import ble, excalidraw, home, playground, youtube


def initialize_pages(app: FastAPI) -> None:
    """Attach all TheBundle pages and publish navigation metadata on app state."""
    initialize_site_pages(app, [home.page, ble.page, youtube.page, excalidraw.page, playground.page])
