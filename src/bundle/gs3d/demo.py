"""bundle.gs3d demo — end-to-end synthesis in under 30 lines.

Run:
    python -m bundle.gs3d.demo
    python -m bundle.gs3d.demo --output-dir /tmp/gs3d_demo
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from bundle.core import logger
from bundle.gs3d.generators import SphereGenerator, TorusGenerator
from bundle.gs3d.ply import read_ply_header, write_ply
from bundle.gs3d.temporal import MotionConfig, TemporalGenerator

log = logger.get_logger(__name__)


async def _run(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)

    # ── 3D: generate a sphere and a torus ─────────────────────────────────
    sphere_ply = out / "sphere.ply"
    torus_ply = out / "torus.ply"

    sphere_meta = await write_ply(sphere_ply, await SphereGenerator(count=20_000, radius=1.0, seed=0).generate())
    torus_meta = await write_ply(
        torus_ply, await TorusGenerator(count=20_000, major_radius=1.5, minor_radius=0.4, seed=1).generate()
    )

    log.info("sphere : %d Gaussians  bbox %s … %s", sphere_meta.num_gaussians, sphere_meta.bbox_min, sphere_meta.bbox_max)
    log.info("torus  : %d Gaussians  bbox %s … %s", torus_meta.num_gaussians, torus_meta.bbox_min, torus_meta.bbox_max)

    # ── header round-trip ─────────────────────────────────────────────────
    head = await read_ply_header(sphere_ply)
    log.info("header : %d Gaussians  sh_degree=%d", head.num_gaussians, head.sh_degree)

    # ── 4D: orbit animation of the sphere ─────────────────────────────────
    seq = await TemporalGenerator(
        ply_path=sphere_ply,
        motion=MotionConfig(motion_type="orbit", amplitude=1.0, frequency=1.0, axis="y"),
        frame_count=30,
        fps=30.0,
        output_dir=out / "orbit",
    ).generate()

    log.info("4D seq : %d frames → %s", seq.frame_count, seq.frames_dir)
    log.info("Demo complete. Files in: %s", out)


@click.command()
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=Path("/tmp/gs3d_demo"), show_default=True)
def main(output_dir: Path) -> None:
    """Run the gs3d demo: sphere, torus, 4D orbit sequence."""
    asyncio.run(_run(output_dir))


if __name__ == "__main__":
    main()
