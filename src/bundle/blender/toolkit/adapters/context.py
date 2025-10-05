"""Context managers and helpers to initialize Blender scripts."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from bundle.core import logger

log = logger.get_logger(__name__)


@contextmanager
def blender_logging_context(name: str) -> Iterator[None]:
    """Ensure Blender-side logging is initialised consistently."""
    log.info("Entering Blender logging context for %s", name)
    try:
        yield
    finally:
        log.info("Exiting Blender logging context for %s", name)
