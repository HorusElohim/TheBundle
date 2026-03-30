"""Visualization stage — base class and I/O contracts."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data

from ..base import Stage
from ..gaussians.base import GaussiansOutput
from ..sfm.base import SfmOutput

log = logger.get_logger(__name__)


class VisualizationInput(Data):
    """Input contract for the visualization stage."""

    gaussians_output: GaussiansOutput
    images_dir: Path
    sfm_output: SfmOutput


class VisualizationOutput(Data):
    """Output contract from the visualization stage."""

    ply_path: Path
    renders_dir: Path

    def validate_exists(self) -> bool:
        if not self.ply_path.exists():
            log.warning("VisualizationOutput missing PLY: %s", self.ply_path)
            return False
        return True


class VisualizationStage(Stage):
    """Base class for cross-platform visualization backends.

    Visualization stages run on any platform (Metal, CPU, CUDA) and produce
    a quick-preview PLY + renders from an existing training workspace.
    """

    name: str = "visualization"
    backend: str = "opensplat"
    experiment_name: str = "preview"

    async def run(self, input: Data) -> Data:
        assert isinstance(input, VisualizationInput)
        return await self._run(input)

    @abstractmethod
    async def _run(self, input: VisualizationInput) -> VisualizationOutput: ...

    @abstractmethod
    async def check_deps(self) -> bool: ...
