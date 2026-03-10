from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
from pathlib import Path

import rich_click as click
from pydantic import PrivateAttr

from bundle.core import data, logger, process, tracer
from bundle.core.entity import Entity

log = logger.get_logger(__name__)

PODS_ROOT_ENV = "BUNDLE_PODS_ROOT"


class PodSpec(data.Data):
    """Declarative specification for a single pod.

    Attributes:
        name: Pod identifier (e.g. "comfyui", "discord-music").
        folder: Subdirectory name under the pods root.
        service: Docker Compose service name, if the compose file defines one matching the pod name.
        buildable: Whether the compose file contains a ``build:`` section.
        containers: Explicit ``container_name`` values parsed from the compose file.
    """

    name: str
    folder: str
    service: str | None = None
    buildable: bool = True
    containers: list[str] = data.Field(default_factory=list)


def _default_pods_root() -> Path | None:
    """Resolve the pods root directory from environment, package layout, or cwd."""
    env_root = os.environ.get(PODS_ROOT_ENV)
    candidates = []
    if env_root:
        candidates.append(Path(env_root))

    package_root = Path(__file__).resolve().parent
    candidates.append(package_root / "pods")

    repo_root = Path(__file__).resolve().parents[3]
    candidates.append(repo_root / "pods")
    candidates.append(Path.cwd() / "pods")

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _resolve_compose_command() -> str:
    """Return the docker compose CLI invocation, preferring v2 plugin syntax."""
    if shutil.which("docker"):
        return "docker compose"
    if shutil.which("docker-compose"):
        return "docker-compose"
    raise click.ClickException("Docker compose is not available. Install Docker and ensure it is on PATH.")


class PodManager(Entity):
    """Manages discovery and orchestration of local AI pods.

    On construction the manager resolves the Docker Compose CLI, scans the
    ``pods_root`` directory for pod folders (each containing a
    ``docker-compose.yml``), and caches the resulting :class:`PodSpec` objects.

    All compose operations (build, run, down, status, logs) are async and
    delegate to :class:`~bundle.core.process.ProcessStream` for streamed output
    or :class:`~bundle.core.process.Process` for captured output.
    """

    pods_root: Path
    _specs: dict[str, PodSpec] = PrivateAttr(default_factory=dict)
    _compose_cmd: str = PrivateAttr(default="")

    @data.model_validator(mode="after")
    def _post_init(self):
        self._compose_cmd = _resolve_compose_command()
        self._specs = self._discover()
        return self

    @classmethod
    def create(cls, pods_root: Path | str | None = None) -> PodManager:
        """Factory that resolves the pods root and returns a ready-to-use manager."""
        root = Path(pods_root) if pods_root else _default_pods_root()
        if root is None:
            raise click.ClickException(
                f"No pods root found. Use --pods-root or set {PODS_ROOT_ENV} to the directory containing pod folders."
            )
        return cls(name="PodManager", pods_root=root.resolve())

    # -- Discovery --

    def _discover(self) -> dict[str, PodSpec]:
        """Scan ``pods_root`` for subdirectories containing a docker-compose.yml."""
        specs: dict[str, PodSpec] = {}
        if not self.pods_root.exists():
            return specs
        for child in sorted(self.pods_root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir():
                continue
            if not (child / "docker-compose.yml").exists():
                continue
            pod_name = child.name.lower()
            specs[pod_name] = self._inspect(pod_name, child)
        return specs

    @staticmethod
    def _inspect(pod_name: str, pod_path: Path) -> PodSpec:
        """Parse a pod's docker-compose.yml to extract service, build, and container metadata."""
        content = (pod_path / "docker-compose.yml").read_text(encoding="utf-8", errors="replace")
        buildable = "build:" in content
        service = None
        target = f"{pod_name}:"
        for line in content.splitlines():
            if line.startswith("  ") and line.strip() == target:
                service = pod_name
                break
        containers = re.findall(r"container_name:\s*(\S+)", content)
        return PodSpec(name=pod_name, folder=pod_name, service=service, buildable=buildable, containers=containers)

    @property
    def specs(self) -> dict[str, PodSpec]:
        return self._specs

    def get(self, name: str) -> PodSpec:
        """Look up a pod by name (case-insensitive). Raises ``ClickException`` if not found."""
        pod = self._specs.get(name.lower())
        if pod is None:
            available = ", ".join(sorted(self._specs.keys())) if self._specs else "none"
            raise click.ClickException(f"Unknown pod '{name}'. Available pods: {available}")
        return pod

    def pod_path(self, pod: PodSpec) -> Path:
        """Resolve and validate the filesystem path for a pod."""
        path = (self.pods_root / pod.folder).resolve()
        if not path.exists():
            raise click.ClickException(
                f"Pod '{pod.name}' was not found at '{path}'. "
                f"Use --pods-root or set {PODS_ROOT_ENV} to the correct location."
            )
        return path

    def running_containers(self) -> set[str]:
        """Query Docker for currently running container names."""
        try:
            result = asyncio.run(process.Process(name="docker.ps")(
                "docker ps --format {{.Names}}"
            ))
            return {line.strip() for line in result.stdout.splitlines() if line.strip()}
        except Exception:
            return set()

    # -- Compose execution --

    async def compose(self, pod: PodSpec, subcommand: str, stream: bool = False) -> process.ProcessResult:
        """Execute a docker compose subcommand against a pod's compose file."""
        cwd = self.pod_path(pod)
        compose_file = cwd / "docker-compose.yml"
        if not compose_file.exists():
            raise click.ClickException(f"docker-compose.yml not found for pod at '{cwd}'.")
        ansi_flag = " --ansi always" if sys.platform != "win32" else ""
        cmd = f'{self._compose_cmd}{ansi_flag} -f "{compose_file}" {subcommand}'
        if pod.service:
            cmd = f"{cmd} {pod.service}"
        runner: process.Process | process.ProcessStream
        runner = process.ProcessStream(name="Pods.compose.stream") if stream else process.Process(name="Pods.compose")
        return await runner(cmd, cwd=str(cwd))

    # -- High-level operations --

    @tracer.Async.decorator.call_raise
    async def build(self, pod: PodSpec) -> process.ProcessResult | None:
        """Build the pod's Docker image. Skips pods that use prebuilt images only."""
        if not pod.buildable:
            log.info("Pod '%s' uses prebuilt images only. Nothing to build.", pod.name)
            return None
        return await self.compose(pod, "build", stream=True)

    @tracer.Async.decorator.call_raise
    async def run(self, pod: PodSpec) -> process.ProcessResult:
        """Start a pod in detached mode (``up -d``)."""
        return await self.compose(pod, "up -d", stream=True)

    @tracer.Async.decorator.call_raise
    async def down(self, pod: PodSpec) -> process.ProcessResult:
        """Stop and remove a pod's containers and networks."""
        return await self.compose(pod, "down", stream=True)

    @tracer.Async.decorator.call_raise
    async def status(self, pod: PodSpec) -> process.ProcessResult:
        """Return the ``docker compose ps`` output for a pod."""
        return await self.compose(pod, "ps", stream=False)

    @tracer.Async.decorator.call_raise
    async def logs(self, pod: PodSpec, follow: bool = True, tail: int = 200) -> process.ProcessResult:
        """Stream or show pod container logs."""
        follow_flag = "-f " if follow else ""
        return await self.compose(pod, f"logs {follow_flag}--tail {tail}", stream=True)
