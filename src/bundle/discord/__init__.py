"""Discord bot module for TheBundle."""

from bundle import BUNDLE_LOGGER
from bundle.core import logger

BUNDLE_LOGGER.level = logger.Level.DEBUG

log = logger.get_logger(__name__)
log.setLevel(logger.Level.DEBUG)
