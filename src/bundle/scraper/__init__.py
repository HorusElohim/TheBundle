from ..core import logger

log = logger.get_logger(__name__)
log.setLevel(logger.Level.VERBOSE)


from . import sites
