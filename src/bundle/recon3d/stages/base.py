"""Abstract base class for pipeline stages."""

from __future__ import annotations

from abc import abstractmethod

from bundle.core import logger
from bundle.core.data import Data
from bundle.core.entity import Entity

log = logger.get_logger(__name__)


class Stage(Entity):
    """Base class for a pipeline stage.

    Each stage wraps an external tool (COLMAP, 3DGRUT, etc.) with a thin
    Python orchestration layer: construct CLI args, run via subprocess, and
    validate the output contract.
    """

    @abstractmethod
    async def run(self, input: Data) -> Data:
        """Execute the stage and return the output contract."""
        ...

    @abstractmethod
    async def check_deps(self) -> bool:
        """Verify that external tools required by this stage are available."""
        ...
