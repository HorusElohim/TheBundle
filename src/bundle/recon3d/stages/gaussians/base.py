"""Gaussian splatting stage — base class and I/O contracts."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data

from ..base import Stage
from ..sfm.base import SfmOutput

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# I/O contracts
# ---------------------------------------------------------------------------


class GaussiansInput(Data):
    """Input contract for the Gaussian splatting training stage."""

    sfm_output: SfmOutput
    images_dir: Path


class GaussiansOutput(Data):
    """Output contract from the Gaussian splatting training stage."""

    checkpoint_path: Path
    ply_path: Path
    renders_dir: Path

    def validate_exists(self) -> bool:
        """Check that all expected output files are present."""
        expected = [self.checkpoint_path, self.ply_path]
        missing = [p for p in expected if not p.exists()]
        if missing:
            log.warning("GaussiansOutput missing files: %s", missing)
            return False
        return True


# ---------------------------------------------------------------------------
# Stage base
# ---------------------------------------------------------------------------


class GaussiansStage(Stage):
    """Base class for Gaussian splatting renderers.

    Subclasses implement ``_run`` with renderer-specific training logic.
    Common validation and output discovery lives here.
    """

    name: str = "gaussians"
    renderer: str = "3dgut"  # "3dgut" | "3dgrt"
    export_usdz: bool = True
    config_name: str = "auto"
    experiment_name: str = "default"

    async def run(self, input: Data) -> Data:
        assert isinstance(input, GaussiansInput)
        return await self._run(input)

    @abstractmethod
    async def _run(self, input: GaussiansInput) -> GaussiansOutput: ...

    @abstractmethod
    async def check_deps(self) -> bool: ...
