import logging
from pathlib import Path
import asyncio  # Added import

import pybind11
from setuptools import Extension

from .config import ModuleConfig
from .pkgconfig import PkgConfig

logger = logging.getLogger(__name__)


class PybindModule:
    def __init__(self, cfg: ModuleConfig) -> None:
        self.cfg = cfg

    async def run_pkg_config(self) -> None:
        if not self.cfg.pkg_config_packages:
            return
        pkgs = tuple(self.cfg.pkg_config_packages)
        dirs = tuple(self.cfg.pkg_config_dirs)
        result = await PkgConfig.run(pkgs, dirs)
        self.cfg.include_dirs.extend(result.include_dirs)
        self.cfg.extra_compile_args.extend(result.compile_flags)
        self.cfg.library_dirs.extend(result.library_dirs)
        self.cfg.libraries.extend(result.libraries)
        self.cfg.extra_link_args.extend(result.link_flags)

    async def to_extension(self, base_dir: Path) -> Extension:
        await self.run_pkg_config()  # await async method
        std_flag = f"-std=c++{self.cfg.cpp_std}"
        if std_flag not in self.cfg.extra_compile_args:
            self.cfg.extra_compile_args.append(std_flag)
        sources = [str((base_dir / s).resolve()) for s in self.cfg.sources]
        inc_dirs = [pybind11.get_include()] + self.cfg.include_dirs
        return Extension(
            name=self.cfg.name,
            sources=sources,
            language=self.cfg.language,
            include_dirs=inc_dirs,
            library_dirs=self.cfg.library_dirs,
            libraries=self.cfg.libraries,
            extra_compile_args=self.cfg.extra_compile_args,
            extra_link_args=self.cfg.extra_link_args,
        )


class PybindProject:
    def __init__(self, modules, base_dir):
        self.base_dir = base_dir
        self.modules = [PybindModule(m) for m in modules]
        self.plugins = []

    def register_plugin(self, p):
        self.plugins.append(p)

    async def apply_plugins(self):
        for m in self.modules:
            for p in self.plugins:
                await p.apply(m)

    async def get_extensions(self):
        await self.apply_plugins()
        # Create extensions concurrently if m.to_extension is independent
        extension_tasks = [m.to_extension(self.base_dir) for m in self.modules]
        return await asyncio.gather(*extension_tasks)
