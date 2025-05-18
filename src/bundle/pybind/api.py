#!/usr/bin/env python
"""
CLI for pybind setuptools helper module, leveraging pkgconfig and pybind11.
"""
import multiprocessing
import os
import platform
import sys
import sysconfig
from pathlib import Path

from bundle.core import logger, tracer
from bundle.core.process import Process
from bundle.pybind.config import PybindConfig
from bundle.pybind.pkgconfig import PkgConfig

log = logger.get_logger(__name__)


class Pybind:
    """A utility class for Pybind11 related operations."""

    @staticmethod
    @tracer.Async.decorator.call_raise
    async def set_pkgconfig_path(install_prefix: Path):
        """
        Sets the PKG_CONFIG_PATH environment variable based on the C++ install prefix.
        This helps setup.py find the .pc files for the just-built C++ libraries.

        Args:
            install_prefix: The CMAKE_INSTALL_PREFIX where C++ libraries were installed.
        """
        pkg_config_dir = install_prefix.resolve() / "lib" / "pkgconfig"
        if pkg_config_dir.is_dir():
            log.info(f"Setting PKG_CONFIG_PATH to include: {pkg_config_dir}")
            await PkgConfig.set_path(pkg_config_dir)
        else:
            log.warning(
                f"PKG_CONFIG_PATH not set: Directory {pkg_config_dir} does not exist. "
                "This might be expected if the C++ project does not generate .pc files."
            )

    @staticmethod
    @tracer.Async.decorator.call_raise
    async def build(path: str, parallel: int = multiprocessing.cpu_count()):
        """
        Build the pybind11 extensions in-place for the given project path.
        """
        proj = Path(path).resolve()
        cmd = f"python {proj / 'setup.py'} build_ext --inplace"
        if parallel:
            cmd += f" --parallel {parallel}"

        log.info(f"Running build command in {proj}:")

        if sys.platform == "darwin":
            arch = platform.machine()
            env = os.environ.copy()
            env["ARCHFLAGS"] = f"-arch {arch}"
            env["MACOSX_DEPLOYMENT_TARGET"] = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET") or "14.0"
        else:
            env = None

        proc = Process()
        result = await proc(cmd, cwd=str(proj), env=env)
        log.info(f"Build completed with return code {result.returncode}")

    @staticmethod
    @tracer.Async.decorator.call_raise
    async def info(path: str):
        """
        Show the current pybind11 configuration for the given project path.
        """
        proj = Path(path).resolve()
        toml_file = proj / "pyproject.toml"
        try:
            cfg = PybindConfig.load_toml(toml_file)
        except Exception as e:
            log.error(f"Failed to load config from {toml_file}: {e}")
            return

        json_text = await cfg.as_json()
        log.info(f"pybind11 configuration from {toml_file}:\n{json_text}")
