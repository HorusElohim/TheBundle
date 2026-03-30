"""OpenSplat visualization backend — Metal / CPU / CUDA quick preview."""

from __future__ import annotations

import shutil
from pathlib import Path

from bundle.core import logger
from bundle.core.process import ProcessStream

from .base import VisualizationInput, VisualizationOutput, VisualizationStage

log = logger.get_logger(__name__)


class OpenSplatVisualization(VisualizationStage):
    """Quick-preview visualization using OpenSplat (Metal / CPU / CUDA).

    Runs a low-iteration OpenSplat pass to produce a preview PLY.
    Uses whatever GPU backend is available — Metal on macOS, CUDA on Linux,
    CPU as universal fallback.
    """

    name: str = "visualization.opensplat"
    num_iters: int = 2_000

    async def _run(self, input: VisualizationInput) -> VisualizationOutput:
        sfm = input.sfm_output
        images_dir = sfm.images_dir if sfm.images_dir else input.images_dir

        staging_dir = input.images_dir.parent / ".opensplat_viz_staging"
        self._prepare_staging(staging_dir, images_dir, sfm.sparse_dir)

        out_dir = input.images_dir.parent / "preview" / self.experiment_name
        out_dir.mkdir(parents=True, exist_ok=True)

        output_ply = out_dir / "preview.ply"

        cmd = f"opensplat {staging_dir} -n {self.num_iters} -o {output_ply}"

        log.info("OpenSplat viz: %d iters → %s", self.num_iters, output_ply)
        proc = ProcessStream()
        await proc(cmd)

        result = VisualizationOutput(
            ply_path=output_ply,
            renders_dir=out_dir,
        )

        if not result.validate_exists():
            raise RuntimeError(f"OpenSplat visualization failed — check {out_dir}")

        log.info("OpenSplat viz: complete — %s", output_ply)
        return result

    async def check_deps(self) -> bool:
        return shutil.which("opensplat") is not None

    @staticmethod
    def _prepare_staging(staging_dir: Path, images_dir: Path, sparse_dir: Path) -> None:
        staging_dir.mkdir(parents=True, exist_ok=True)

        images_link = staging_dir / "images"
        if not images_link.exists():
            images_link.symlink_to(images_dir)

        sparse_parent = staging_dir / "sparse"
        sparse_parent.mkdir(parents=True, exist_ok=True)

        model_link = sparse_parent / sparse_dir.name
        if not model_link.exists():
            model_link.symlink_to(sparse_dir)
