"""Structure-from-Motion stage — base class and I/O contracts."""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from pathlib import Path

from pydantic import field_validator

from bundle.core import logger
from bundle.core.data import Data

from ..base import Stage

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SfmBackend(str, Enum):
    """Supported Structure-from-Motion backends."""

    COLMAP = "colmap"
    PYCUSFM = "pycusfm"


# ---------------------------------------------------------------------------
# I/O contracts
# ---------------------------------------------------------------------------


class SfmInput(Data):
    """Input contract for the Structure-from-Motion stage."""

    images_dir: Path
    initial_poses: Path | None = None  # required for pyCuSFM, optional for COLMAP

    @field_validator("images_dir")
    @classmethod
    def _images_must_exist(cls, v: Path) -> Path:
        if not v.is_dir():
            raise ValueError(f"images_dir does not exist: {v}")
        return v


class SfmOutput(Data):
    """Output contract from the Structure-from-Motion stage.

    The sparse reconstruction follows the COLMAP convention:
        sparse_dir/
            cameras.bin
            images.bin
            points3D.bin
    """

    sparse_dir: Path
    database_path: Path
    images_dir: Path | None = None  # undistorted images (if undistortion was run)
    backend: SfmBackend

    def validate_exists(self) -> bool:
        """Check that all expected output files are present."""
        expected = [
            self.sparse_dir / "cameras.bin",
            self.sparse_dir / "images.bin",
            self.sparse_dir / "points3D.bin",
            self.database_path,
        ]
        missing = [p for p in expected if not p.exists()]
        if missing:
            log.warning("SfmOutput missing files: %s", missing)
            return False
        return True


# ---------------------------------------------------------------------------
# Stage base
# ---------------------------------------------------------------------------


class SfmStage(Stage):
    """Base class for SfM backends.

    Subclasses implement ``_run`` with the backend-specific pipeline.
    Common validation and setup lives here.
    """

    name: str = "sfm"
    backend: SfmBackend = SfmBackend.COLMAP
    use_gpu: bool = True
    matcher: str = "exhaustive"  # "exhaustive" | "sequential"
    undistort: bool = True  # run image_undistorter to produce PINHOLE cameras

    async def run(self, input: Data) -> Data:
        assert isinstance(input, SfmInput)
        return await self._run(input)

    @abstractmethod
    async def _run(self, input: SfmInput) -> SfmOutput: ...

    @abstractmethod
    async def check_deps(self) -> bool: ...
