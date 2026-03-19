"""CLI for the Recon3D pipeline module."""

from __future__ import annotations

import json
from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer

from .contracts import GaussiansInput, SfmBackend, SfmInput, Workspace

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def recon3d():
    """3D reconstruction pipeline — SfM, Gaussian Splatting, USD export."""
    pass


# ---------------------------------------------------------------------------
# bundle recon3d run
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--sfm-backend", type=click.Choice(["colmap", "pycusfm"]), default="colmap", help="SfM backend.")
@click.option("--renderer", type=click.Choice(["3dgut", "3dgrt"]), default="3dgut", help="Gaussian renderer.")
@click.option("--export-usdz/--no-export-usdz", default=True, help="Export USDZ after training.")
@tracer.Sync.decorator.call_raise
async def run(workspace: Path, sfm_backend: str, renderer: str, export_usdz: bool):
    """Run the full reconstruction pipeline: SfM -> Gaussians -> USD."""
    from .pipeline import Pipeline

    ws = Workspace(root=workspace)
    pipeline = Pipeline.default(
        workspace=ws,
        sfm_backend=SfmBackend(sfm_backend),
        renderer=renderer,
        export_usdz=export_usdz,
    )
    results = await pipeline.run()
    for name, output in results.items():
        log.info("Stage '%s' output: %s", name, output)


# ---------------------------------------------------------------------------
# bundle recon3d sfm
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--backend", type=click.Choice(["colmap", "pycusfm"]), default="colmap", help="SfM backend.")
@click.option("--use-gpu/--no-gpu", default=True, help="Enable GPU acceleration.")
@tracer.Sync.decorator.call_raise
async def sfm(workspace: Path, backend: str, use_gpu: bool):
    """Run only the Structure-from-Motion stage."""
    from .stages.sfm import SfmStage

    ws = Workspace(root=workspace)
    ws.ensure_dirs()
    stage = SfmStage(backend=SfmBackend(backend), use_gpu=use_gpu)

    if not await stage.check_deps():
        raise click.ClickException(f"SfM backend '{backend}' is not available on this system.")

    input_contract = SfmInput(images_dir=ws.images_dir)
    output = await stage.run(input_contract)
    log.info("SfM output: %s", output)


# ---------------------------------------------------------------------------
# bundle recon3d gaussians
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--config", "config_name", default="apps/colmap_3dgut.yaml", help="Hydra config name.")
@click.option("--experiment", default="default", help="Experiment name for output directory.")
@click.option("--renderer", type=click.Choice(["3dgut", "3dgrt"]), default="3dgut", help="Gaussian renderer.")
@click.option("--export-usdz/--no-export-usdz", default=True, help="Export USDZ after training.")
@tracer.Sync.decorator.call_raise
async def gaussians(workspace: Path, config_name: str, experiment: str, renderer: str, export_usdz: bool):
    """Run only the Gaussian splatting training stage."""
    from .contracts import SfmOutput
    from .stages.gaussians import GaussiansStage

    ws = Workspace(root=workspace)
    # Require SfM output to already exist
    sfm_out = SfmOutput(
        sparse_dir=ws.sfm_dir / "sparse" / "0",
        database_path=ws.sfm_dir / "database.db",
        backend=SfmBackend.COLMAP,
    )
    if not sfm_out.validate_exists():
        raise click.ClickException("SfM output not found — run 'bundle recon3d sfm' first.")

    stage = GaussiansStage(renderer=renderer, export_usdz=export_usdz)

    if not await stage.check_deps():
        raise click.ClickException("3DGRUT is not available on this system.")

    input_contract = GaussiansInput(
        sfm_output=sfm_out,
        images_dir=ws.images_dir,
        config_name=config_name,
        experiment_name=experiment,
    )
    output = await stage.run(input_contract)
    log.info("Gaussians output: %s", output)


# ---------------------------------------------------------------------------
# bundle recon3d status
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@tracer.Sync.decorator.call_raise
async def status(workspace: Path):
    """Show pipeline status for a workspace."""
    ws = Workspace(root=workspace)
    if not ws.manifest_path.exists():
        log.info("No pipeline manifest found at %s", ws.manifest_path)
        return

    manifest = json.loads(ws.manifest_path.read_text())
    stages = manifest.get("stages", {})

    if not stages:
        log.info("No stages have completed yet.")
        return

    for name, info in stages.items():
        log.info(
            "  %s — completed %s (%.1fs)",
            name,
            info.get("completed_at", "?"),
            info.get("elapsed_seconds", 0),
        )
