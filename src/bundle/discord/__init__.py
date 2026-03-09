"""Discord bot module for TheBundle."""

from bundle.core import logger
from bundle import BUNDLE_LOGGER

BUNDLE_LOGGER.level = logger.Level.DEBUG

log = logger.get_logger(__name__)
log.setLevel(logger.Level.DEBUG)
