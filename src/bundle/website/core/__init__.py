"""Public API for website core application composition."""

from .app import create_app
from .manifest import SiteManifest
from .pages import PageDefinition, initialize_pages, mount_page

__all__ = ["create_app", "SiteManifest", "PageDefinition", "mount_page", "initialize_pages"]
