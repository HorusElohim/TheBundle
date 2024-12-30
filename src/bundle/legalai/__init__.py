from bundle.core import logger
from bundle import BUNDLE_LOGGER

log = logger.get_logger(__name__)

log.parent = BUNDLE_LOGGER

log.setLevel(logger.Level.VERBOSE)

log.debug("LegalAI started")
