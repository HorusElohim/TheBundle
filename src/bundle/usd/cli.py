"""CLI for the USD module."""

from __future__ import annotations

from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def usd():
    """OpenUSD scene building and export utilities."""
    pass


@usd.command(name="export")
@click.option("--input", "input_path", type=click.Path(path_type=Path, exists=True), required=True, help="Input PLY file.")
@click.option("--output", "output_path", type=click.Path(path_type=Path), required=True, help="Output USDZ file path.")
@tracer.Sync.decorator.call_raise
async def export_cmd(input_path: Path, output_path: Path):
    """Convert a PLY point cloud to USDZ."""
    from .export import ply_to_usdz

    result = await ply_to_usdz(input_path, output_path)
    log.info("Exported: %s", result)
