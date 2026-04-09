"""Blender environment data model."""

from __future__ import annotations

from pathlib import Path

from bundle.core import data


class BlenderEnvironment(data.Data):
    """Describes a discovered Blender installation."""

    blender_executable: Path
    python_executable: Path
    scripts_dir: Path

    @property
    def site_packages(self) -> Path:
        return self.scripts_dir / "modules"
