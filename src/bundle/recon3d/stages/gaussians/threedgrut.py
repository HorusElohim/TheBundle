"""3DGRUT Gaussian splatting backend."""

from __future__ import annotations

from pathlib import Path

from bundle.core import logger
from bundle.core.process import ProcessStream

from .base import GaussiansInput, GaussiansOutput, GaussiansStage

log = logger.get_logger(__name__)

# Maps (sfm_backend, renderer) → Hydra config name
_CONFIG_MAP: dict[tuple[str, str], str] = {
    ("colmap", "3dgut"): "apps/colmap_3dgut.yaml",
    ("colmap", "3dgrt"): "apps/colmap_3dgrt.yaml",
    ("pycusfm", "3dgut"): "apps/cusfm_3dgut.yaml",
    ("pycusfm", "3dgrt"): "apps/cusfm_3dgut.yaml",  # no separate RT config for cusfm
}


class ThreeDGrutGaussians(GaussiansStage):
    """3DGRUT training and optional USDZ export.

    Supports two renderers:
        - 3DGUT (Unscented Transform) — fast rasterization, any CUDA GPU
        - 3DGRT (Ray Tracing) — volumetric, needs RT cores
    """

    name: str = "gaussians.3dgrut"
    grut_dir: str = "/opt/3dgrut"

    async def _run(self, input: GaussiansInput) -> GaussiansOutput:
        sfm = input.sfm_output

        # 3DGRUT's COLMAP data loader expects:
        #   staging/images/     → source images (undistorted preferred)
        #   staging/sparse/0/   → COLMAP binary model
        #
        # Our workspace may have sfm_output/sparse/0 separate from images/.
        # Symlink both into a staging dir to match the expected layout.
        # Prefer undistorted images/sparse if the SfM stage produced them.
        images_dir = sfm.images_dir if sfm.images_dir else input.images_dir
        staging_dir = input.images_dir.parent / ".3dgrut_staging"
        self._prepare_staging(staging_dir, images_dir, sfm.sparse_dir)

        # Resolve config name
        backend_key = sfm.backend.value
        config_name = self.config_name
        if config_name == "auto":
            config_name = _CONFIG_MAP.get(
                (backend_key, self.renderer),
                "apps/colmap_3dgut.yaml",
            )

        # Output directory
        out_dir = input.images_dir.parent / "runs"
        out_dir.mkdir(parents=True, exist_ok=True)

        train_script = f"{self.grut_dir}/train.py"
        proc = ProcessStream()

        overrides = [
            f"path={staging_dir}",
            f"out_dir={out_dir}",
            f"experiment_name={self.experiment_name}",
        ]

        cmd = f"python {train_script} --config-name {config_name} {' '.join(overrides)}"

        log.info("3DGRUT: training with config=%s, renderer=%s", config_name, self.renderer)
        log.info("3DGRUT: staging dir=%s, output=%s/%s", staging_dir, out_dir, self.experiment_name)
        await proc(cmd)

        exp_dir = out_dir / self.experiment_name
        result = self._find_outputs(exp_dir)

        log.info("3DGRUT: training complete — %s", exp_dir)
        return result

    async def check_deps(self) -> bool:
        try:
            import threedgrut

            return True
        except ImportError:
            return False

    @staticmethod
    def _prepare_staging(staging_dir: Path, images_dir: Path, sparse_dir: Path) -> None:
        """Create a staging directory with symlinks matching 3DGRUT's expected layout."""
        staging_dir.mkdir(parents=True, exist_ok=True)

        images_link = staging_dir / "images"
        if not images_link.exists():
            images_link.symlink_to(images_dir)

        # sparse_dir is e.g. sfm_output/sparse/0 — we need staging/sparse/0/
        sparse_parent = staging_dir / "sparse"
        sparse_parent.mkdir(parents=True, exist_ok=True)

        model_link = sparse_parent / sparse_dir.name  # "0"
        if not model_link.exists():
            model_link.symlink_to(sparse_dir)

    @staticmethod
    def _find_outputs(exp_dir: Path) -> GaussiansOutput:
        """Locate checkpoint, PLY, and renders in the experiment directory."""
        checkpoint = exp_dir / "checkpoint.pth"
        ply = exp_dir / "model.ply"
        renders = exp_dir / "renders"

        # 3DGRUT may use slightly different names — search if defaults missing
        if not checkpoint.exists():
            pth_files = list(exp_dir.rglob("*.pth"))
            if pth_files:
                checkpoint = pth_files[0]

        if not ply.exists():
            ply_files = list(exp_dir.rglob("*.ply"))
            if ply_files:
                ply = ply_files[0]

        result = GaussiansOutput(
            checkpoint_path=checkpoint,
            ply_path=ply,
            renders_dir=renders,
        )

        if not result.validate_exists():
            log.warning("3DGRUT output incomplete — some files may still be generating")

        return result
