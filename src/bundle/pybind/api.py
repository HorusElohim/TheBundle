#!/usr/bin/env python
"""
CLI for pybind setuptools helper module, leveraging pkgconfig and pybind11.
"""
import multiprocessing
import os
import platform
import sysconfig
import sys
from pathlib import Path

from bundle.core import logger, tracer
from bundle.core.process import Process
from bundle.pybind.config import PybindConfig
from bundle.pybind.pkgconfig import set_pkg_config_path  # type: ignore

log = logger.get_logger(__name__)


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
