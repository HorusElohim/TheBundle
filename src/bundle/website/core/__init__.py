"""Public API for website core application composition."""

from .app import create_app
from .manifest import SiteManifest
from .pages import Page, initialize_pages, mount_page

__all__ = ["Page", "SiteManifest", "create_app", "initialize_pages", "mount_page"]
