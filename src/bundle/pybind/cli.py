#!/usr/bin/env python
"""
CLI for pybind setuptools helper module, leveraging pkgconfig and pybind11.
"""

import multiprocessing

import rich_click as click

from bundle.core import logger, tracer
from bundle.pybind import Pybind

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
    default=multiprocessing.cpu_count(),
    help="Number of parallel build jobs.",
)
@tracer.Sync.decorator.call_raise
async def build(path: str, parallel: int):
    """
    Build the pybind11 extensions in-place for the given project path.
    """
    await Pybind.build(path, parallel=parallel)


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
    await Pybind.info(path)
