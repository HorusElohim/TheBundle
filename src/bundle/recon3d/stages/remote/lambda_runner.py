"""Lambda Labs remote runner — trains Gaussians via bundle.lambdalabs."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data
from bundle.lambdalabs import LambdaLabsConfig, RemoteJob

from ..base import Stage
from ..gaussians.base import GaussiansInput, GaussiansOutput

log = logger.get_logger(__name__)

_REMOTE_JOBS_ROOT = Path("/home/ubuntu/bundle_jobs")


class LambdaRunner(Stage):
    """Runs Gaussian splatting training on a Lambda Labs GPU instance.

    Uses ``bundle.lambdalabs.RemoteJob`` for the full lifecycle:
        1. Launch instance (or attach to existing via instance_id)
        2. Wait until active
        3. Install bundle on the remote
        4. Upload local workspace
        5. Run ``bundle recon3d gaussians`` remotely
        6. Download results
        7. Terminate instance (if auto_terminate=True)

    Set LAMBDA_API_KEY in env or configure via ``bundle lambdalabs setup``.
    """

    name: str = "gaussians.lambda"
    renderer: str = "3dgut"
    experiment_name: str = "default"
    config_name: str = "auto"
    export_usdz: bool = True
    # If set, attach to this existing instance instead of launching a new one.
    instance_id: str | None = None
    # Terminate instance after job completes.
    auto_terminate: bool = False
    # SSH key path on local machine (defaults to ~/.ssh/id_rsa).
    ssh_key_path: Path | None = None
    # Lambda Labs filesystem name. If set (or configured in ~/.bundle/lambdalabs.json),
    # the workspace is stored on the persistent NFS volume — images and SfM output
    # are uploaded once and reused across jobs.
    filesystem_name: str | None = None

    model_config = Data.model_config.copy()
    model_config["arbitrary_types_allowed"] = True

    async def run(self, input: Data) -> Data:
        assert isinstance(input, GaussiansInput)
        return await self._run(input)

    async def _run(self, input: GaussiansInput) -> GaussiansOutput:
        local_ws = input.images_dir.parent
        job_id = f"job_{int(time.time())}"
        remote_ws = _REMOTE_JOBS_ROOT / job_id

        cfg = LambdaLabsConfig.load()
        job = RemoteJob(
            config=cfg,
            ssh_key_path=self.ssh_key_path,
            auto_terminate=self.auto_terminate,
            filesystem_name=self.filesystem_name,
        )

        # 1. Attach to existing or launch new instance
        await job.launch(instance_id=self.instance_id)

        # 2. Wait for active + IP
        await job.wait()

        # 3. Install bundle on remote
        await job.setup()

        # 4. Upload workspace
        await job.upload(local=local_ws, remote=remote_ws)

        # 5. Run training remotely
        usdz_flag = "--export-usdz" if self.export_usdz else "--no-export-usdz"
        train_cmd = (
            f"bundle recon3d gaussians "
            f"--workspace {remote_ws} "
            f"--renderer {self.renderer} "
            f"--experiment {self.experiment_name} "
            f"--config {self.config_name} "
            f"{usdz_flag}"
        )
        await job.run(train_cmd)

        # 6. Download results
        await job.download(remote=remote_ws / "runs", local=local_ws / "runs")

        # 7. Optionally terminate
        if self.auto_terminate:
            await job.terminate()

        exp_dir = local_ws / "runs" / self.experiment_name
        return self._find_outputs(exp_dir)

    async def check_deps(self) -> bool:
        return bool(shutil.which("rsync") and shutil.which("ssh"))

    @staticmethod
    def _find_outputs(exp_dir: Path) -> GaussiansOutput:
        checkpoint = exp_dir / "checkpoint.pth"
        ply = exp_dir / "model.ply"
        renders = exp_dir / "renders"

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
            log.warning("Lambda: output incomplete — some files may be missing in %s", exp_dir)
        return result
