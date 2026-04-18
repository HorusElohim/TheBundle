"""Faster-GS Gaussian splatting backend.

Runs inside the ``recon3d/gaussians/fastergs`` pod via the ``train_fastergs.py``
wrapper, which mirrors the CLI shape of 3dgrut's ``train.py``. Host-side this
stage looks almost identical to :class:`ThreeDGrutGaussians` — swapping the
container entry point is the only real change.
"""

from __future__ import annotations

from bundle.core import logger
from bundle.core.process import ProcessStream

from .base import GaussiansInput, GaussiansOutput, GaussiansStage

log = logger.get_logger(__name__)


class FasterGsGaussians(GaussiansStage):
    """Faster-GS training stage (CVPR 2026).

    Targets 3–5× speedup over vanilla 3DGS with comparable quality. The
    upstream package lives inside the NeRFICG framework; the pod's
    ``train_fastergs.py`` wrapper handles config generation and patching so
    this stage can invoke a single command.
    """

    name: str = "gaussians.fastergs"
    wrapper_script: str = "/opt/train_fastergs.py"

    async def _run(self, input: GaussiansInput) -> GaussiansOutput:
        sfm = input.sfm_output
        scene_root = sfm.sparse_dir.parent.parent
        out_dir = input.images_dir.parent / "runs"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = (
            f"python {self.wrapper_script}"
            f" --path {scene_root}"
            f" --out-dir {out_dir}"
            f" --experiment {self.experiment_name}"
        )

        log.info("Faster-GS: training scene=%s -> %s/%s", scene_root, out_dir, self.experiment_name)
        await ProcessStream()(cmd)

        exp_dir = out_dir / self.experiment_name
        ply = exp_dir / "model.ply"
        if not ply.exists():
            candidates = list(exp_dir.rglob("*.ply"))
            if candidates:
                ply = candidates[0]

        checkpoint = exp_dir / "checkpoint.pth"
        if not checkpoint.exists():
            candidates = list(exp_dir.rglob("*.pth"))
            if candidates:
                checkpoint = candidates[0]

        result = GaussiansOutput(
            checkpoint_path=checkpoint,
            ply_path=ply,
            renders_dir=exp_dir / "renders",
        )
        if not result.validate_exists():
            log.warning("Faster-GS output incomplete — some files may still be generating")

        log.info("Faster-GS: training complete — %s", exp_dir)
        return result

    async def check_deps(self) -> bool:
        try:
            import fastergs  # noqa: F401

            return True
        except ImportError:
            return False
