"""Lambda Labs remote runner — trains Gaussians on a remote GPU instance."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data
from bundle.core.entity import Entity
from bundle.core.process import ProcessStream

from ..base import Stage
from ..gaussians.base import GaussiansInput, GaussiansOutput

log = logger.get_logger(__name__)


class LambdaConfig(Entity):
    """Connection config for a pre-existing Lambda Labs GPU instance."""

    instance_ip: str
    ssh_user: str = "ubuntu"
    ssh_key_path: Path | None = None
    remote_workspace_root: Path = Path("/home/ubuntu/lambda_jobs")
    api_key: str = ""

    @classmethod
    def from_env(cls) -> LambdaConfig:
        import os

        ip = os.environ.get("LAMBDA_INSTANCE_IP", "")
        if not ip:
            raise RuntimeError("LAMBDA_INSTANCE_IP environment variable is required")
        return cls(
            instance_ip=ip,
            api_key=os.environ.get("LAMBDA_API_KEY", ""),
        )

    @property
    def ssh_target(self) -> str:
        return f"{self.ssh_user}@{self.instance_ip}"

    @property
    def ssh_key_flag(self) -> str:
        if self.ssh_key_path:
            return f"-i {self.ssh_key_path}"
        return ""

    def ssh_cmd(self, remote_cmd: str) -> str:
        key = f" {self.ssh_key_flag}" if self.ssh_key_flag else ""
        return f"ssh{key} -o StrictHostKeyChecking=no {self.ssh_target} '{remote_cmd}'"

    def rsync_up(self, local: Path, remote: Path) -> str:
        key = f" {self.ssh_key_flag}" if self.ssh_key_flag else ""
        return f"rsync -avz --progress -e 'ssh{key} -o StrictHostKeyChecking=no' {local}/ {self.ssh_target}:{remote}/"

    def rsync_down(self, remote: Path, local: Path) -> str:
        key = f" {self.ssh_key_flag}" if self.ssh_key_flag else ""
        return f"rsync -avz --progress -e 'ssh{key} -o StrictHostKeyChecking=no' {self.ssh_target}:{remote}/ {local}/"


class LambdaRunner(Stage):
    """Runs a Gaussians training stage on a remote Lambda Labs GPU instance.

    Lifecycle:
        1. rsync local workspace → remote:/home/ubuntu/lambda_jobs/<job_id>/
        2. SSH: bundle recon3d gaussians --workspace <remote_path> --renderer <renderer>
        3. rsync remote runs/ → local runs/
        4. Return a GaussiansOutput pointing at local paths.

    Requires rsync and ssh on the local machine.
    The remote instance must have the bundle package installed.
    """

    name: str = "gaussians.lambda"
    config: LambdaConfig
    renderer: str = "3dgut"
    experiment_name: str = "default"
    config_name: str = "auto"
    export_usdz: bool = True

    model_config = Data.model_config.copy()
    model_config["arbitrary_types_allowed"] = True

    async def run(self, input: Data) -> Data:
        assert isinstance(input, GaussiansInput)
        return await self._run(input)

    async def _run(self, input: GaussiansInput) -> GaussiansOutput:
        job_id = f"job_{int(time.time())}"
        remote_ws = self.config.remote_workspace_root / job_id
        local_ws = input.images_dir.parent
        proc = ProcessStream()

        # 1. Create remote workspace
        log.info("Lambda: creating remote workspace %s", remote_ws)
        await proc(self.config.ssh_cmd(f"mkdir -p {remote_ws}"))

        # 2. rsync images + sfm output up
        log.info("Lambda: uploading workspace → %s:%s", self.config.instance_ip, remote_ws)
        await proc(self.config.rsync_up(local_ws, remote_ws))

        # 3. Run training remotely
        usdz_flag = "--export-usdz" if self.export_usdz else "--no-export-usdz"
        remote_cmd = (
            f"bundle recon3d gaussians "
            f"--workspace {remote_ws} "
            f"--renderer {self.renderer} "
            f"--experiment {self.experiment_name} "
            f"--config {self.config_name} "
            f"{usdz_flag}"
        )
        log.info("Lambda: running training — %s", remote_cmd)
        await proc(self.config.ssh_cmd(remote_cmd))

        # 4. rsync runs/ back
        remote_runs = remote_ws / "runs"
        local_runs = local_ws / "runs"
        local_runs.mkdir(parents=True, exist_ok=True)
        log.info("Lambda: downloading results ← %s", remote_runs)
        await proc(self.config.rsync_down(remote_runs, local_runs))

        # 5. Locate outputs locally
        exp_dir = local_runs / self.experiment_name
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
