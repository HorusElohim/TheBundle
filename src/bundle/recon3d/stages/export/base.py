"""Export stage — base class and I/O contracts."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data

from ..base import Stage

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# I/O contracts
# ---------------------------------------------------------------------------


class ExportInput(Data):
    """Input contract for USD export."""

    ply_path: Path
    output_path: Path


class ExportOutput(Data):
    """Output contract from USD export."""

    usdz_path: Path

    def validate_exists(self) -> bool:
        if not self.usdz_path.exists():
            log.warning("ExportOutput missing: %s", self.usdz_path)
            return False
        return True


# ---------------------------------------------------------------------------
# Stage base
# ---------------------------------------------------------------------------


class ExportStage(Stage):
    """Base class for scene export backends (USDZ, glTF, etc.)."""

    name: str = "export"
    format: str = "usdz"

    async def run(self, input: Data) -> Data:
        assert isinstance(input, ExportInput)
        return await self._run(input)

    @abstractmethod
    async def _run(self, input: ExportInput) -> ExportOutput: ...

    @abstractmethod
    async def check_deps(self) -> bool: ...
