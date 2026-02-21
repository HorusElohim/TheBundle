"""TheBundle site manifest wiring."""

from __future__ import annotations

from ...core.manifest import SiteManifest
from ...core.static import default_components_path, default_static_path
from .pages import initialize_pages


def site_manifest() -> SiteManifest:
    """Return the manifest for the default TheBundle website site."""
    return SiteManifest(
        title="Bundle Website",
        static_path=default_static_path(),
        components_path=default_components_path(),
        initialize_pages=initialize_pages,
    )

