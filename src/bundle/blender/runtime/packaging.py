"""Utilities to package configuration and toolkit payloads for Blender."""

from __future__ import annotations

from pathlib import Path

from bundle.core import logger

log = logger.get_logger(__name__)


def build_payload(_: Path) -> Path:
    """Placeholder that will eventually assemble payload archives."""
    log.error("Payload assembly is not implemented")
    raise NotImplementedError("Payload assembly not implemented yet")
