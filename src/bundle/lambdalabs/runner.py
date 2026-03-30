"""Lambda Labs remote job runner — full lifecycle management."""

from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path

from bundle.core import logger
from bundle.core.process import ProcessStream

from .client import LambdaClient
from .config import LambdaLabsConfig
from .models import Instance

log = logger.get_logger(__name__)

BUNDLE_INSTALL_CMD = (
    "pip install --quiet thebundle 2>/dev/null || "
    "pip install --quiet git+https://github.com/HorusElohim/TheBundle.git 2>/dev/null"
)


class RemoteJob:
    """Manages a single remote training job on Lambda Labs.

    Lifecycle:
        1. launch()  — start a GPU instance (or attach to an existing one)
        2. wait()    — poll until active + has IP
        3. setup()   — install bundle on the remote instance
        4. upload()  — rsync local workspace → remote
        5. run()     — execute a command via SSH
        6. download()— rsync remote results → local
        7. terminate()— shut down the instance (optional)
    """

    def __init__(
        self,
        config: LambdaLabsConfig | None = None,
        api_key: str | None = None,
        ssh_key_path: Path | None = None,
        ssh_user: str = "ubuntu",
        auto_terminate: bool = False,
    ):
        cfg = config or LambdaLabsConfig.load()
        self._api_key = api_key or cfg.api_key
        if not self._api_key:
            raise RuntimeError("No Lambda Labs API key — run: bundle lambdalabs setup --api-key KEY")
        self.config = cfg
        self.ssh_key_path = ssh_key_path or Path.home() / ".ssh" / "id_rsa"
        self.ssh_user = ssh_user
        self.auto_terminate = auto_terminate
        self.instance: Instance | None = None

    async def launch(
        self,
        instance_type: str | None = None,
        ssh_key_name: str | None = None,
        region: str | None = None,
        name: str | None = None,
        instance_id: str | None = None,
    ) -> Instance:
        """Launch a new instance or attach to an existing one by ID."""
        async with LambdaClient(self._api_key) as client:
            if instance_id:
                log.info("Attaching to existing instance %s", instance_id)
                self.instance = await client.get_instance(instance_id)
            else:
                itype = instance_type or self.config.default_instance_type
                key = ssh_key_name or self.config.default_ssh_key
                reg = region or self.config.default_region
                job_name = name or f"bundle-job-{int(time.time())}"
                log.info("Launching %s in %s (key: %s)", itype, reg, key)
                ids = await client.launch(
                    instance_type_name=itype,
                    ssh_key_names=[key],
                    region_name=reg,
                    name=job_name,
                )
                if not ids:
                    raise RuntimeError("Launch returned no instance IDs")
                self.instance = await client.get_instance(ids[0])
                log.info("Launched instance %s", self.instance.id)
        return self.instance

    async def wait(self, timeout: float = 600) -> Instance:
        """Poll until the instance is active with an IP."""
        if not self.instance:
            raise RuntimeError("No instance — call launch() first")
        async with LambdaClient(self._api_key) as client:
            self.instance = await client.wait_active(self.instance.id, timeout=timeout)
        log.info("Instance ready: %s @ %s", self.instance.id[:8], self.instance.ip)
        return self.instance

    async def setup(self) -> None:
        """Install bundle on the remote instance."""
        log.info("Installing bundle on remote instance...")
        await self._ssh(BUNDLE_INSTALL_CMD)
        log.info("Bundle installed on remote instance")

    async def upload(self, local: Path, remote: Path) -> None:
        """rsync local directory → remote instance."""
        if not self.instance or not self.instance.ip:
            raise RuntimeError("Instance not ready — call wait() first")
        log.info("Uploading %s → %s:%s", local, self.instance.ip, remote)
        await self._ssh(f"mkdir -p {remote}")
        cmd = self._rsync(f"{local}/", f"{self.ssh_user}@{self.instance.ip}:{remote}/")
        proc = ProcessStream()
        await proc(cmd)

    async def download(self, remote: Path, local: Path) -> None:
        """rsync remote directory → local."""
        if not self.instance or not self.instance.ip:
            raise RuntimeError("Instance not ready — call wait() first")
        log.info("Downloading %s:%s → %s", self.instance.ip, remote, local)
        local.mkdir(parents=True, exist_ok=True)
        cmd = self._rsync(f"{self.ssh_user}@{self.instance.ip}:{remote}/", f"{local}/")
        proc = ProcessStream()
        await proc(cmd)

    async def run(self, command: str) -> None:
        """Execute a shell command on the remote instance via SSH."""
        log.info("Remote exec: %s", command)
        await self._ssh(command)

    async def terminate(self) -> None:
        """Terminate the instance."""
        if not self.instance:
            return
        async with LambdaClient(self._api_key) as client:
            await client.terminate([self.instance.id])
        log.info("Terminated instance %s", self.instance.id)
        self.instance = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _ssh_target(self) -> str:
        return f"{self.ssh_user}@{self.instance.ip}"

    def _ssh_opts(self) -> str:
        opts = "-o StrictHostKeyChecking=no -o ConnectTimeout=10"
        if self.ssh_key_path.exists():
            opts += f" -i {self.ssh_key_path}"
        return opts

    async def _ssh(self, command: str) -> None:
        if not self.instance or not self.instance.ip:
            raise RuntimeError("Instance not ready")
        full = f"ssh {self._ssh_opts()} {self._ssh_target} '{command}'"
        proc = ProcessStream()
        await proc(full)

    def _rsync(self, src: str, dst: str) -> str:
        opts = f"-e 'ssh {self._ssh_opts()}'"
        return f"rsync -avz --progress {opts} {src} {dst}"
