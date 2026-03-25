"""OpenSplat Gaussian splatting backend (Metal / CPU / CUDA)."""

from __future__ import annotations

import shutil
from pathlib import Path

from bundle.core import logger
from bundle.core.process import ProcessStream

from .base import GaussiansInput, GaussiansOutput, GaussiansStage

log = logger.get_logger(__name__)


class OpenSplatGaussians(GaussiansStage):
    """OpenSplat training — runs on Metal (macOS), CPU, or CUDA.

    Wraps the ``opensplat`` CLI which accepts a COLMAP project directory
    and outputs a ``.ply`` point cloud.
    """

    name: str = "gaussians.opensplat"
    num_iters: int = 30_000

    async def _run(self, input: GaussiansInput) -> GaussiansOutput:
        sfm = input.sfm_output
        images_dir = sfm.images_dir if sfm.images_dir else input.images_dir

        # OpenSplat expects a COLMAP project directory:
        #   staging/images/      → source images
        #   staging/sparse/0/    → COLMAP binary model
        staging_dir = input.images_dir.parent / ".opensplat_staging"
        self._prepare_staging(staging_dir, images_dir, sfm.sparse_dir)

        out_dir = input.images_dir.parent / "runs" / self.experiment_name
        out_dir.mkdir(parents=True, exist_ok=True)

        output_ply = out_dir / "model.ply"

        cmd = f"opensplat {staging_dir} -n {self.num_iters} -o {output_ply}"

        log.info("OpenSplat: training %d iterations", self.num_iters)
        log.info("OpenSplat: staging=%s, output=%s", staging_dir, output_ply)

        proc = ProcessStream()
        await proc(cmd)

        result = GaussiansOutput(
            checkpoint_path=output_ply,  # OpenSplat has no separate checkpoint
            ply_path=output_ply,
            renders_dir=out_dir,
        )

        if not result.validate_exists():
            raise RuntimeError(f"OpenSplat output validation failed — check {out_dir}")

        log.info("OpenSplat: training complete — %s", output_ply)
        return result

    async def check_deps(self) -> bool:
        return shutil.which("opensplat") is not None

    @staticmethod
    def _prepare_staging(staging_dir: Path, images_dir: Path, sparse_dir: Path) -> None:
        """Create a staging directory with symlinks matching COLMAP project layout."""
        staging_dir.mkdir(parents=True, exist_ok=True)

        images_link = staging_dir / "images"
        if not images_link.exists():
            images_link.symlink_to(images_dir)

        sparse_parent = staging_dir / "sparse"
        sparse_parent.mkdir(parents=True, exist_ok=True)

        model_link = sparse_parent / sparse_dir.name
        if not model_link.exists():
            model_link.symlink_to(sparse_dir)
