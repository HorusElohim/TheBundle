"""Workspace layout for a Recon3D reconstruction job."""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator

from bundle.core.data import Data


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
    def preview_dir(self) -> Path:
        return self.root / "preview"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    def run_dir(self, experiment: str = "default") -> Path:
        return self.runs_dir / experiment

    def ensure_dirs(self) -> None:
        """Create the workspace directory tree if it does not exist."""
        for d in (self.images_dir, self.sfm_dir, self.runs_dir, self.export_dir, self.preview_dir):
            d.mkdir(parents=True, exist_ok=True)
