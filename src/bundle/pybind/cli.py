#!/usr/bin/env python
"""
CLI for pybind setuptools helper module, leveraging pkgconfig and pybind11.
"""

import rich_click as click
from pathlib import Path

from bundle.core import logger, tracer
from bundle.core.process import Process
from bundle.pybind.config import PybindConfig

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def pybind():
    """Manage pybind11 build tasks."""
    pass


@pybind.command()
@click.option(
    "--path",
    "-d",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Project root directory (where setup.py & pyproject.toml live).",
)
@click.option(
    "--parallel",
    "-p",
    type=int,
    default=None,
    help="Number of parallel build jobs.",
)
@tracer.Sync.decorator.call_raise
async def build(path: str, parallel: int):
    """
    Build the pybind11 extensions in-place for the given project path.
    """
    proj = Path(path).resolve()
    cmd = f"python {proj / 'setup.py'} build_ext --inplace"
    if parallel:
        cmd += f" --parallel {parallel}"

    log.info(f"Running build command in {proj}:")
    log.debug(cmd)

    proc = Process()
    result = await proc(cmd, cwd=str(proj))
    log.info(f"Build completed with return code {result.returncode}")


@pybind.command()
@click.option(
    "--path",
    "-d",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=".",
    help="Project root directory (where pyproject.toml lives).",
)
@tracer.Sync.decorator.call_raise
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
