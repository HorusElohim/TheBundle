from ..core import setup_logging

LOGGER = setup_logging(name="bundle_player", level=10)

from . import config
from . import track
from .app import main
