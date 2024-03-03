from ..core import logger

LOGGER = logger.setup_logging(name=__name__, level=logger.logging.DEBUG)

from . import config
from . import track
from .app import main
