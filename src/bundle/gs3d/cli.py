"""CLI for the bundle.gs3d module.

Commands
--------
bundle gs3d generate  -- synthesise a Gaussian cloud from a primitive or mesh
bundle gs3d animate   -- apply a 4D motion to a static PLY and emit a frame sequence
bundle gs3d info      -- print metadata from a PLY header (no array load)
"""

from __future__ import annotations

from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer

from .generators import available_shapes

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def gs3d():
    """Synthetic 3D/4D Gaussian splatting — generate, animate, inspect."""
    pass


# ---------------------------------------------------------------------------
# bundle gs3d generate
# ---------------------------------------------------------------------------


@gs3d.command()
@click.option(
    "--shape",
    type=click.Choice(available_shapes()),
    required=True,
    help="Primitive shape or 'mesh' for mesh-to-Gaussian conversion.",
)
@click.option("--output", "-o", type=click.Path(path_type=Path), required=True, help="Output PLY path.")
@click.option("--count", default=10_000, show_default=True, help="Number of Gaussians to emit.")
@click.option("--sh-degree", default=3, show_default=True, help="Spherical harmonics degree (0..3).")
@click.option("--seed", default=None, type=int, help="Random seed for reproducibility.")
@click.option("--opacity", default=2.0, show_default=True, help="Logit-space opacity (2.0 ≈ alpha 0.88).")
@click.option("--color", default="1.0,1.0,1.0", show_default=True, help="Linear RGB colour as 'r,g,b'.")
# Sphere options
@click.option("--radius", default=1.0, show_default=True, help="[sphere] Radius.")
@click.option("--surface/--no-surface", default=True, help="[sphere/cube] Surface vs. volume sampling.")
# Cube options
@click.option("--size", default=1.0, show_default=True, help="[cube] Edge length.")
# Torus options
@click.option("--major-radius", default=1.0, show_default=True, help="[torus] Major radius R.")
@click.option("--minor-radius", default=0.3, show_default=True, help="[torus] Minor (tube) radius r.")
# Mesh options
@click.option("--source", default=None, type=click.Path(path_type=Path), help="[mesh] Input mesh file.")
@tracer.Sync.decorator.call_raise
async def generate(
    shape: str,
    output: Path,
    count: int,
    sh_degree: int,
    seed: int | None,
    opacity: float,
    color: str,
    radius: float,
    surface: bool,
    size: float,
    major_radius: float,
    minor_radius: float,
    source: Path | None,
) -> None:
    """Generate a synthetic Gaussian splat cloud and write it to a PLY file."""
    from .generators import create_generator
    from .ply import write_ply

    try:
        r, g, b = (float(c) for c in color.split(","))
    except ValueError as exc:
        raise click.BadParameter("--color must be 'r,g,b' (three floats, e.g. '1.0,0.5,0.2')") from exc

    shared = dict(count=count, sh_degree=sh_degree, seed=seed, opacity=opacity, color=(r, g, b))

    shape_kwargs: dict = {}
    if shape == "sphere":
        shape_kwargs = dict(radius=radius, surface=surface)
    elif shape == "cube":
        shape_kwargs = dict(size=size, surface=surface)
    elif shape == "torus":
        shape_kwargs = dict(major_radius=major_radius, minor_radius=minor_radius)
    elif shape == "mesh":
        if source is None:
            raise click.UsageError("--source is required when --shape mesh")
        shape_kwargs = dict(source=source)

    gen = create_generator(shape, **shared, **shape_kwargs)
    cloud = await gen.generate()
    meta = await write_ply(output, cloud)
    log.info("Wrote %d Gaussians → %s", meta.num_gaussians, meta.path)


# ---------------------------------------------------------------------------
# bundle gs3d info
# ---------------------------------------------------------------------------


@gs3d.command()
@click.argument("ply", type=click.Path(path_type=Path, exists=True))
@tracer.Sync.decorator.call_raise
async def info(ply: Path) -> None:
    """Print metadata from a PLY file header (no array payload loaded)."""
    from .ply import read_ply_header

    meta = await read_ply_header(ply)
    log.info("File         : %s", meta.path)
    log.info("Gaussians    : %d", meta.num_gaussians)
    log.info("SH degree    : %d", meta.sh_degree)
    log.info("Bbox min     : %s", meta.bbox_min)
    log.info("Bbox max     : %s", meta.bbox_max)


# ---------------------------------------------------------------------------
# bundle gs3d animate
# ---------------------------------------------------------------------------


@gs3d.command()
@click.option("--input", "-i", "ply_in", type=click.Path(path_type=Path, exists=True), required=True, help="Input PLY.")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory for per-frame PLY output.",
)
@click.option(
    "--motion",
    type=click.Choice(["rigid", "oscillate", "explode", "orbit"]),
    default="orbit",
    show_default=True,
    help="Motion type.",
)
@click.option("--frames", default=30, show_default=True, help="Number of frames.")
@click.option("--fps", default=30.0, show_default=True, help="Playback frame rate (metadata only).")
@click.option("--amplitude", default=1.0, show_default=True, help="Motion amplitude (metres / radians).")
@click.option("--frequency", default=1.0, show_default=True, help="Motion frequency (cycles per second).")
@click.option("--axis", default="y", type=click.Choice(["x", "y", "z"]), show_default=True, help="Motion axis.")
@tracer.Sync.decorator.call_raise
async def animate(
    ply_in: Path,
    output_dir: Path,
    motion: str,
    frames: int,
    fps: float,
    amplitude: float,
    frequency: float,
    axis: str,
) -> None:
    """Apply a 4D motion to a static PLY and write a frame sequence."""
    from .temporal import MotionConfig, TemporalGenerator

    cfg = MotionConfig(
        motion_type=motion,
        amplitude=amplitude,
        frequency=frequency,
        axis=axis,
    )
    gen = TemporalGenerator(
        ply_path=ply_in,
        motion=cfg,
        frame_count=frames,
        fps=fps,
        output_dir=output_dir,
    )
    seq = await gen.generate()
    log.info("Wrote %d frames → %s", seq.frame_count, seq.frames_dir)
