from __future__ import annotations

from pathlib import Path
from typing import List, Union

import toml

from bundle.core import data


class ModuleConfig(data.Data):
    """
    Configuration for a single pybind11 extension module.
    """

    name: str
    sources: List[str]
    language: str = "c++"
    pkg_config_packages: List[str] = data.Field(default_factory=list)
    pkg_config_dirs: List[str] = data.Field(default_factory=list)
    cpp_std: str = "20"
    include_dirs: List[str] = data.Field(default_factory=list)
    library_dirs: List[str] = data.Field(default_factory=list)
    libraries: List[str] = data.Field(default_factory=list)
    extra_compile_args: List[str] = data.Field(default_factory=list)
    extra_link_args: List[str] = data.Field(default_factory=list)


class PybindConfig(data.Data):
    """
    Root configuration holding all ModuleConfig entries.
    """

    modules: List[ModuleConfig]

    @classmethod
    def load_toml(cls, pyproject_toml: Union[str, Path]) -> PybindConfig:
        """
        Load and validate the [tool.pybind11] section from the given pyproject.toml path.
        """
        p = Path(pyproject_toml)
        if not p.exists():
            raise FileNotFoundError(f"{p} does not exist")
        raw = toml.load(p)
        section = raw.get("tool", {}).get("pybind11")
        if section is None:
            raise KeyError("Missing [tool.pybind11] in pyproject.toml")
        return cls(**section)
