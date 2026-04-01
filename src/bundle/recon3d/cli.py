"""CLI for the Recon3D pipeline module."""

from __future__ import annotations

import json
from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer

from .stages.gaussians.base import GaussiansInput
from .stages.sfm.base import SfmBackend, SfmInput
from .workspace import Workspace

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def recon3d():
    """3D reconstruction pipeline — SfM, Gaussian Splatting, USD export."""
    pass


# ---------------------------------------------------------------------------
# bundle recon3d data
# ---------------------------------------------------------------------------


@click.group(name="data")
@tracer.Sync.decorator.call_raise
async def data_group():
    """Manage datasets for the reconstruction pipeline."""
    pass


recon3d.add_command(data_group)


@data_group.command(name="fetch")
@click.option("--dataset", type=click.Choice(["360_v2"]), default="360_v2", help="Dataset to download.")
@click.option(
    "--data-root",
    type=click.Path(path_type=Path),
    default="/workspace/data",
    envvar="RECON3D_DATA_ROOT",
    help="Root directory for dataset storage (or set RECON3D_DATA_ROOT).",
)
@tracer.Sync.decorator.call_raise
async def data_fetch(dataset: str, data_root: Path):
    """Download and extract a benchmark dataset."""
    from .datasets import DatasetId, fetch

    info = await fetch(DatasetId(dataset), data_root)
    log.info("Dataset '%s' ready at %s", info.dataset_id.value, info.root)
    log.info("Available scenes: %s", ", ".join(info.scenes))


@data_group.command(name="list")
@click.option(
    "--data-root",
    type=click.Path(path_type=Path),
    default="/workspace/data",
    envvar="RECON3D_DATA_ROOT",
    help="Root directory for dataset storage.",
)
@tracer.Sync.decorator.call_raise
async def data_list(data_root: Path):
    """List downloaded datasets and available scenes."""
    from .datasets import DATASET_REGISTRY, DatasetId, _is_scene

    data_root = data_root.resolve()
    for ds_id in DatasetId:
        _, _, known_scenes = DATASET_REGISTRY[ds_id]
        found = [s for s in known_scenes if (data_root / s).is_dir()]
        if found:
            all_scenes = sorted(p.name for p in data_root.iterdir() if p.is_dir() and _is_scene(p))
            log.info("%s — %s (%d scenes: %s)", ds_id.value, data_root, len(all_scenes), ", ".join(all_scenes))
        else:
            log.info("%s — not downloaded", ds_id.value)


@data_group.command(name="locate")
@click.argument("scene", type=str)
@click.option(
    "--data-root",
    type=click.Path(path_type=Path),
    default="/workspace/data",
    envvar="RECON3D_DATA_ROOT",
    help="Root directory for dataset storage.",
)
@tracer.Sync.decorator.call_raise
async def data_locate(scene: str, data_root: Path):
    """Print the images directory for a specific scene."""
    from .datasets import locate_scene

    images_dir = locate_scene(data_root.resolve(), scene)
    log.info("%s", images_dir)


# ---------------------------------------------------------------------------
# bundle recon3d run
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--sfm-backend", type=click.Choice(["colmap", "pycusfm"]), default="colmap", help="SfM backend.")
@click.option(
    "--renderer",
    type=click.Choice(["auto", "3dgut", "3dgrt"]),
    default="auto",
    help="Gaussian training renderer (CUDA required).",
)
@click.option("--export-usdz/--no-export-usdz", default=True, help="Export USDZ after training.")
@click.option("--lambda/--no-lambda", "use_lambda", default=False, help="Run training on Lambda Labs GPU.")
@click.option(
    "--instance-id",
    default=None,
    envvar="LAMBDA_INSTANCE_ID",
    help="Attach to an existing Lambda instance ID instead of launching a new one.",
)
@click.option("--auto-terminate/--no-auto-terminate", default=False, help="Terminate Lambda instance after training.")
@click.option(
    "--filesystem",
    default=None,
    envvar="LAMBDA_FILESYSTEM",
    help="Lambda filesystem name for persistent workspace storage (skips re-uploading images/SfM).",
)
@click.option("--visualize/--no-visualize", default=True, help="Run local OpenSplat preview after training.")
@click.option("--vis-iters", default=2_000, help="OpenSplat iterations for visualization preview.")
@click.option("--blender/--no-blender", default=False, help="Import final PLY into Blender and save a .blend file.")
@tracer.Sync.decorator.call_raise
async def run(
    workspace: Path,
    sfm_backend: str,
    renderer: str,
    export_usdz: bool,
    use_lambda: bool,
    instance_id: str | None,
    auto_terminate: bool,
    filesystem: str | None,
    visualize: bool,
    vis_iters: int,
    blender: bool,
):
    """Run the full reconstruction pipeline: SfM -> Train (CUDA) -> [Visualize] -> [Blender]."""
    from .pipeline import Pipeline

    ws = Workspace(root=workspace)
    pipeline = Pipeline.default(
        workspace=ws,
        sfm_backend=SfmBackend(sfm_backend),
        renderer=renderer,
        export_usdz=export_usdz,
        use_lambda=use_lambda,
        lambda_instance_id=instance_id,
        lambda_auto_terminate=auto_terminate,
        lambda_filesystem=filesystem,
        visualize=visualize,
        vis_iters=vis_iters,
        blender=blender,
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
@click.option("--matcher", type=click.Choice(["exhaustive", "sequential"]), default="exhaustive", help="Matching strategy.")
@tracer.Sync.decorator.call_raise
async def sfm(workspace: Path, backend: str, use_gpu: bool, matcher: str):
    """Run only the Structure-from-Motion stage."""
    from .stages.sfm import create_sfm_stage

    ws = Workspace(root=workspace)
    ws.ensure_dirs()
    stage = create_sfm_stage(backend=SfmBackend(backend), use_gpu=use_gpu, matcher=matcher)

    if not await stage.check_deps():
        raise click.ClickException(f"SfM backend '{backend}' is not available on this system.")

    input_contract = SfmInput(images_dir=ws.images_dir)
    output = await stage.run(input_contract)
    log.info("SfM output: %s", output)


# ---------------------------------------------------------------------------
# bundle recon3d gaussians  (CUDA training)
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--config", "config_name", default="auto", help="Hydra config name (auto selects from backend + renderer).")
@click.option("--experiment", default="default", help="Experiment name for output directory.")
@click.option(
    "--renderer",
    type=click.Choice(["auto", "3dgut", "3dgrt"]),
    default="auto",
    help="Gaussian training renderer (CUDA required).",
)
@click.option("--export-usdz/--no-export-usdz", default=True, help="Export USDZ after training.")
@click.option("--lambda/--no-lambda", "use_lambda", default=False, help="Run training on Lambda Labs GPU.")
@click.option(
    "--instance-id",
    default=None,
    envvar="LAMBDA_INSTANCE_ID",
    help="Attach to an existing Lambda instance ID instead of launching a new one.",
)
@click.option("--auto-terminate/--no-auto-terminate", default=False, help="Terminate Lambda instance after training.")
@click.option(
    "--filesystem",
    default=None,
    envvar="LAMBDA_FILESYSTEM",
    help="Lambda filesystem name for persistent workspace storage.",
)
@tracer.Sync.decorator.call_raise
async def gaussians(
    workspace: Path,
    config_name: str,
    experiment: str,
    renderer: str,
    export_usdz: bool,
    use_lambda: bool,
    instance_id: str | None,
    auto_terminate: bool,
    filesystem: str | None,
):
    """Run only the Gaussian splatting training stage (CUDA or Lambda)."""
    from .stages.sfm.base import SfmOutput

    ws = Workspace(root=workspace)
    sfm_out = SfmOutput(
        sparse_dir=ws.sfm_dir / "sparse" / "0",
        database_path=ws.sfm_dir / "database.db",
        backend=SfmBackend.COLMAP,
    )
    if not sfm_out.validate_exists():
        raise click.ClickException("SfM output not found — run 'bundle recon3d sfm' first.")

    if use_lambda:
        from .stages.remote.lambda_runner import LambdaRunner

        stage = LambdaRunner(
            renderer=renderer if renderer != "auto" else "3dgut",
            experiment_name=experiment,
            config_name=config_name,
            export_usdz=export_usdz,
            instance_id=instance_id,
            auto_terminate=auto_terminate,
            filesystem_name=filesystem,
        )
    else:
        from .stages.gaussians import create_gaussians_stage

        stage = create_gaussians_stage(
            renderer=renderer,
            export_usdz=export_usdz,
            config_name=config_name,
            experiment_name=experiment,
        )

    if not await stage.check_deps():
        raise click.ClickException(f"Stage '{stage.name}' is not available on this system.")

    input_contract = GaussiansInput(
        sfm_output=sfm_out,
        images_dir=ws.images_dir,
    )
    output = await stage.run(input_contract)
    log.info("Gaussians output: %s", output)


# ---------------------------------------------------------------------------
# bundle recon3d visualize  (any platform: Metal / CPU / CUDA)
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--experiment", default="default", help="Training experiment to visualize.")
@click.option("--backend", type=click.Choice(["opensplat"]), default="opensplat", help="Visualization backend.")
@click.option("--num-iters", default=2_000, help="Iterations for the quick preview pass.")
@tracer.Sync.decorator.call_raise
async def visualize(workspace: Path, experiment: str, backend: str, num_iters: int):
    """Run a quick visualization preview (Metal / CPU / CUDA — any platform)."""
    from .stages.gaussians.base import GaussiansOutput
    from .stages.sfm.base import SfmOutput
    from .stages.visualization import create_visualization_stage
    from .stages.visualization.base import VisualizationInput

    ws = Workspace(root=workspace)
    sfm_out = SfmOutput(
        sparse_dir=ws.sfm_dir / "sparse" / "0",
        database_path=ws.sfm_dir / "database.db",
        backend=SfmBackend.COLMAP,
    )
    exp_dir = ws.runs_dir / experiment
    gauss_out = GaussiansOutput(
        checkpoint_path=exp_dir / "checkpoint.pth",
        ply_path=exp_dir / "model.ply",
        renders_dir=exp_dir / "renders",
    )

    stage = create_visualization_stage(backend=backend, num_iters=num_iters)
    if not await stage.check_deps():
        raise click.ClickException(f"Visualization backend '{backend}' is not available on this system.")

    inp = VisualizationInput(
        gaussians_output=gauss_out,
        images_dir=ws.images_dir,
        sfm_output=sfm_out,
    )
    output = await stage.run(inp)
    log.info("Visualization output: %s", output)


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


# ---------------------------------------------------------------------------
# bundle recon3d blender
# ---------------------------------------------------------------------------


@recon3d.command()
@click.option("--workspace", type=click.Path(path_type=Path), required=True, help="Workspace root directory.")
@click.option("--experiment", default="default", help="Training experiment name.")
@click.option("--render/--no-render", default=False, help="Render the scene after import.")
@click.option(
    "--engine",
    type=click.Choice(["EEVEE", "CYCLES"]),
    default="EEVEE",
    help="Render engine.",
)
@tracer.Sync.decorator.call_raise
async def blender(workspace: Path, experiment: str, render: bool, engine: str):
    """Import a trained 3DGS PLY into Blender and save a .blend file."""
    from .stages.blender.base import BlenderInput, BlenderStage
    from .stages.gaussians.base import GaussiansOutput

    ws = Workspace(root=workspace)
    exp_dir = ws.runs_dir / experiment
    gauss_out = GaussiansOutput(
        checkpoint_path=exp_dir / "checkpoint.pth",
        ply_path=exp_dir / "model.ply",
        renders_dir=exp_dir / "renders",
    )

    stage = BlenderStage()
    if not await stage.check_deps():
        raise click.ClickException("Blender not found — install it or set BUNDLE_BLENDER_EXECUTABLE.")

    inp = BlenderInput(
        gaussians_output=gauss_out,
        blend_output=ws.root / "blender" / "scene.blend",
        render=render,
        engine=engine,
    )
    output = await stage.run(inp)
    log.info("Blender output: %s", output)
