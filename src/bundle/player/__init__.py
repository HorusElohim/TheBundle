from ..core import setup_logging

LOGGER = setup_logging(name="bundle_player", level=10)

from .player import BundlePlayer
