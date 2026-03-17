# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

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

IMAGE_PREFIX = "thebundle"


class PodSpec(data.Data):
    """Declarative specification for a single pod.

    Attributes:
        name: Leaf folder name for display (e.g. "website", "colmap").
        folder: Subdirectory name under the pods root (legacy compat, same as full_path).
        full_path: Relative path from pods root using ``/`` separators (e.g. "services/website").
        category: First path segment (e.g. "services", "bases", "recon3d").
        service: Docker Compose service name, if the compose file defines one matching the pod name.
        buildable: Whether the compose file contains a ``build:`` section.
        containers: Explicit ``container_name`` values parsed from the compose file.
    """

    name: str
    folder: str
    full_path: str = ""
    category: str = ""
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


def _parse_from_image(dockerfile: Path) -> str | None:
    """Extract the primary external base image name (without tag) from a Dockerfile.

    Collects all ``FROM`` directives, builds a set of internal stage aliases
    (names after ``AS``), then returns the first ``FROM`` target that is *not*
    an internal alias.  The tag portion (``:latest``, ``:${BASE_TAG}``, etc.)
    is stripped so callers can match on image name alone.
    """
    if not dockerfile.exists():
        return None
    content = dockerfile.read_text(encoding="utf-8", errors="replace")
    froms: list[str] = []
    aliases: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("FROM "):
            parts = stripped.split()
            if len(parts) >= 2:
                froms.append(parts[1])
            # Collect AS alias
            upper = stripped.upper()
            if " AS " in upper:
                alias = stripped.split()[-1]
                aliases.add(alias.lower())
    # Return the first FROM that is not a reference to an internal stage
    for image in froms:
        if image.lower() not in aliases:
            return image.split(":")[0]
    return None


class PodManager(Entity):
    """Manages discovery and orchestration of local AI pods.

    On construction the manager resolves the Docker Compose CLI, scans the
    ``pods_root`` directory recursively for pod folders (each containing a
    ``docker-compose.yml``), and caches the resulting :class:`PodSpec` objects.

    Pods are identified by their relative path from ``pods_root`` using slash
    notation (e.g. ``services/website``, ``bases/cpu``).  Short names are
    supported when unambiguous.

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
        """Recursively scan ``pods_root`` for directories containing a docker-compose.yml."""
        specs: dict[str, PodSpec] = {}
        if not self.pods_root.exists():
            return specs
        for compose_file in sorted(self.pods_root.rglob("docker-compose.yml")):
            pod_dir = compose_file.parent
            rel = pod_dir.relative_to(self.pods_root)
            # Use forward-slash notation regardless of OS
            full_path = rel.as_posix()
            parts = full_path.split("/")
            category = parts[0] if len(parts) > 1 else ""
            leaf_name = parts[-1]
            specs[full_path] = self._inspect(leaf_name, pod_dir, full_path, category)
        return specs

    @staticmethod
    def _inspect(pod_name: str, pod_path: Path, full_path: str, category: str) -> PodSpec:
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
        return PodSpec(
            name=pod_name,
            folder=full_path,
            full_path=full_path,
            category=category,
            service=service,
            buildable=buildable,
            containers=containers,
        )

    @property
    def specs(self) -> dict[str, PodSpec]:
        return self._specs

    def get(self, name: str) -> PodSpec:
        """Look up a pod by full path or short name (case-insensitive).

        Resolution order:
        1. Exact full_path match (e.g. ``services/website``)
        2. Unique leaf-name match (e.g. ``website`` if unambiguous)

        Raises ``ClickException`` if not found or ambiguous.
        """
        key = name.lower().strip("/")
        # Exact full_path match
        if key in self._specs:
            return self._specs[key]
        # Short name: search by leaf name
        matches = [spec for spec in self._specs.values() if spec.name.lower() == key]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            paths = ", ".join(sorted(m.full_path for m in matches))
            raise click.ClickException(f"Ambiguous pod name '{name}'. Matches: {paths}. Use the full path.")
        available = ", ".join(sorted(self._specs.keys())) if self._specs else "none"
        raise click.ClickException(f"Unknown pod '{name}'. Available pods: {available}")

    def pod_path(self, pod: PodSpec) -> Path:
        """Resolve and validate the filesystem path for a pod."""
        path = (self.pods_root / pod.folder).resolve()
        if not path.exists():
            raise click.ClickException(
                f"Pod '{pod.name}' was not found at '{path}'. Use --pods-root or set {PODS_ROOT_ENV} to the correct location."
            )
        return path

    async def running_containers(self) -> set[str]:
        """Query Docker for currently running container names."""
        try:
            result = await process.Process(name="docker.ps")("docker ps --format {{.Names}}")
            return {line.strip() for line in result.stdout.splitlines() if line.strip()}
        except Exception:
            return set()

    # -- Category & dependency helpers --

    @staticmethod
    def image_tag(spec: PodSpec) -> str:
        """Derive the Docker image tag for a pod: ``thebundle/<full_path>:latest``."""
        return f"{IMAGE_PREFIX}/{spec.full_path}:latest"

    @staticmethod
    def image_name(spec: PodSpec) -> str:
        """Derive the Docker image name (without tag) for a pod: ``thebundle/<full_path>``."""
        return f"{IMAGE_PREFIX}/{spec.full_path}"

    def categories(self) -> list[str]:
        """Return the sorted list of discovered categories."""
        return sorted({s.category for s in self._specs.values() if s.category})

    def by_category(self, category: str) -> list[PodSpec]:
        """Return all pods belonging to *category*."""
        return [s for s in self._specs.values() if s.category == category]

    def build_order(self, category: str) -> list[PodSpec]:
        """Return pods in *category* sorted by dependency order (topological sort on FROM lines).

        Parses each pod's Dockerfile to determine which sibling it depends on,
        then sorts so parents are built before children.
        """
        pods = {s.full_path: s for s in self._specs.values() if s.category == category}
        if not pods:
            return []

        # Map full_path → FROM image
        depends_on: dict[str, str | None] = {}
        for fp, spec in pods.items():
            dockerfile = self.pods_root / spec.folder / "Dockerfile"
            depends_on[fp] = _parse_from_image(dockerfile)

        # Map image name (tagless) → full_path so we can resolve FROM → sibling pod
        name_to_fp: dict[str, str] = {}
        for fp, spec in pods.items():
            name_to_fp[self.image_name(spec)] = fp

        # Topological sort (Kahn's algorithm)
        graph: dict[str, list[str]] = {fp: [] for fp in pods}
        in_degree: dict[str, int] = {fp: 0 for fp in pods}
        for fp, from_image in depends_on.items():
            if from_image and from_image in name_to_fp:
                parent_fp = name_to_fp[from_image]
                graph[parent_fp].append(fp)
                in_degree[fp] += 1

        queue = sorted(fp for fp, deg in in_degree.items() if deg == 0)
        ordered: list[str] = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for child in sorted(graph[node]):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return [pods[fp] for fp in ordered]

    @tracer.Async.decorator.call_raise
    async def build_category(self, category: str) -> None:
        """Build all buildable pods in *category* respecting dependency order."""
        order = self.build_order(category)
        if not order:
            available = ", ".join(self.categories()) if self.categories() else "none"
            raise click.ClickException(f"No pods found in category '{category}'. Available categories: {available}")
        buildable = [s for s in order if s.buildable]
        if not buildable:
            log.info("No buildable pods in category '%s'.", category)
            return
        log.info("Building %d pods in '%s': %s", len(buildable), category, " → ".join(s.name for s in buildable))
        for spec in buildable:
            log.info("Building: %s (%s)", spec.full_path, self.image_tag(spec))
            await self.compose(spec, "build", stream=True)

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
        try:
            return await runner(cmd, cwd=str(cwd))
        except process.ProcessError as exc:
            # Convert to a clean ClickException so the tracer doesn't re-log
            # the full stdout/stderr at every layer of the call stack.
            stderr = exc.result.stderr if exc.result else ""
            hint = self._check_missing_image_error(stderr)
            if hint:
                raise click.ClickException(hint) from None
            # Generic failure: show just the stderr (Docker's error), not the full dump
            error_lines = stderr.strip().splitlines() if stderr else []
            # Find the most relevant error line (usually "failed to solve: ...")
            summary = next((line for line in error_lines if "failed to" in line.lower() or "error" in line.lower()), None)
            if not summary and error_lines:
                summary = error_lines[-1]
            msg = f"Pod '{pod.full_path}' compose {subcommand} failed."
            if summary:
                msg += f"\n{summary.strip()}"
            raise click.ClickException(msg) from None

    @staticmethod
    def _check_missing_image_error(stderr: str) -> str | None:
        """If stderr indicates a missing thebundle image, return a helpful hint string."""
        # Only match thebundle/ images in lines that indicate a pull/resolve failure
        match = re.search(
            r"(?:pull access denied|failed to resolve source metadata)\S*\s+\S*?(thebundle/[\w/.-]+(?::[\w.-]+)?)",
            stderr,
        )
        if not match:
            # Fallback: "failed to solve: thebundle/X:tag:"
            match = re.search(r"failed to solve:\s*(thebundle/[\w/.-]+(?::[\w.-]+)?)", stderr)
        if not match:
            return None
        image = match.group(1)
        name_no_tag = image.split(":")[0]
        pod_path = name_no_tag.replace(f"{IMAGE_PREFIX}/", "")
        category = pod_path.split("/")[0] if "/" in pod_path else None
        hint = f"Image '{image}' not found locally. Run 'bundle pods build {pod_path}' first."
        if category:
            hint += f"\nOr 'bundle pods build {category}' to build the whole category."
        return hint

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
