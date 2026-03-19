"""Data contracts for the Recon3D pipeline stages.

Each contract describes a filesystem layout produced or consumed by a pipeline stage.
Stages produce files on disk; contracts validate their existence and provide typed access.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import field_validator

from bundle.core import logger
from bundle.core.data import Data

log = logger.get_logger(__name__)


class SfmBackend(str, Enum):
    """Supported Structure-from-Motion backends."""

    COLMAP = "colmap"
    PYCUSFM = "pycusfm"


class GaussianRenderer(str, Enum):
    """Supported Gaussian splatting renderers."""

    DGUT = "3dgut"
    DGRT = "3dgrt"


class Workspace(Data):
    """Root workspace for a reconstruction job.

    Provides property accessors for the canonical subdirectory layout:
        workspace/
            images/
            sfm_output/
            runs/<experiment>/
            export/
            manifest.json
    """

    root: Path
    name: str = "default"

    @field_validator("root")
    @classmethod
    def _resolve_root(cls, v: Path) -> Path:
        return v.resolve()

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def sfm_dir(self) -> Path:
        return self.root / "sfm_output"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def export_dir(self) -> Path:
        return self.root / "export"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def run_dir(self, experiment: str = "default") -> Path:
        return self.runs_dir / experiment

    def ensure_dirs(self) -> None:
        """Create the workspace directory tree if it does not exist."""
        for d in (self.images_dir, self.sfm_dir, self.runs_dir, self.export_dir):
            d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# SfM stage contracts
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
# Gaussians stage contracts
# ---------------------------------------------------------------------------


class GaussiansInput(Data):
    """Input contract for the Gaussian splatting training stage."""

    sfm_output: SfmOutput
    images_dir: Path
    config_name: str = "apps/colmap_3dgut.yaml"
    experiment_name: str = "default"


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
# Export contracts
# ---------------------------------------------------------------------------


class ExportInput(Data):
    """Input contract for USD export."""

    ply_path: Path
    output_path: Path
