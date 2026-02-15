import asyncio
import os
import shutil
from pathlib import Path

import rich_click as click

from bundle.core import data, logger, process, tracer

log = logger.get_logger(__name__)

PODS_ROOT_ENV = "BUNDLE_PODS_ROOT"


class PodSpec(data.Data):
    """Declarative pod definition."""

    name: str
    folder: str
    service: str | None = None
    buildable: bool = True


class PodsContext(data.Data):
    pods_root: str | None = None


def _default_pods_root() -> Path | None:
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


def _get_context(ctx: click.Context) -> PodsContext:
    context = ctx.obj
    if isinstance(context, PodsContext):
        return context
    return PodsContext()


def _resolve_pods_root(ctx: PodsContext) -> Path:
    root = Path(ctx.pods_root) if ctx.pods_root else _default_pods_root()
    if root is None:
        raise click.ClickException(
            f"No pods root found. Use --pods-root or set {PODS_ROOT_ENV} to the directory containing pod folders."
        )
    return root.resolve()


def _inspect_pod(pod_name: str, pod_path: Path) -> PodSpec:
    compose_path = pod_path / "docker-compose.yml"
    if not compose_path.exists():
        raise click.ClickException(f"docker-compose.yml not found for pod at '{pod_path}'.")

    content = compose_path.read_text(encoding="utf-8", errors="replace")
    buildable = "build:" in content

    service = None
    target = f"{pod_name}:"
    for line in content.splitlines():
        if line.startswith("  ") and line.strip() == target:
            service = pod_name
            break

    return PodSpec(name=pod_name, folder=pod_name, service=service, buildable=buildable)


def _discover_pod_specs(root: Path) -> dict[str, PodSpec]:
    specs: dict[str, PodSpec] = {}
    if not root.exists():
        return specs

    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir():
            continue
        compose_path = child / "docker-compose.yml"
        if not compose_path.exists():
            continue
        pod_name = child.name.lower()
        specs[pod_name] = _inspect_pod(pod_name, child)
    return specs


def _resolve_pod_spec(ctx: PodsContext, pod_name: str) -> PodSpec:
    root = _resolve_pods_root(ctx)
    specs = _discover_pod_specs(root)
    pod = specs.get(pod_name.lower())
    if pod is None:
        available = ", ".join(sorted(specs.keys())) if specs else "none"
        raise click.ClickException(f"Unknown pod '{pod_name}'. Available pods: {available}")
    return pod


def _resolve_pod_path(ctx: PodsContext, pod: PodSpec) -> Path:
    root = _resolve_pods_root(ctx)
    pod_path = (root / pod.folder).resolve()
    if not pod_path.exists():
        raise click.ClickException(
            f"Pod '{pod.name}' was not found at '{pod_path}'. "
            f"Use --pods-root or set {PODS_ROOT_ENV} to the correct location."
        )
    return pod_path


def _resolve_compose_command() -> str:
    if shutil.which("docker"):
        return "docker compose"
    if shutil.which("docker-compose"):
        return "docker-compose"
    raise click.ClickException("Docker compose is not available. Install Docker and ensure it is on PATH.")


def _compose_file(pod_path: Path) -> Path:
    compose_path = pod_path / "docker-compose.yml"
    if not compose_path.exists():
        raise click.ClickException(f"docker-compose.yml not found for pod at '{pod_path}'.")
    return compose_path


async def _run_compose(command: str, cwd: Path, stream: bool = False) -> process.ProcessResult:
    runner: process.Process | process.ProcessStream
    runner = process.ProcessStream(name="Pods.compose.stream") if stream else process.Process(name="Pods.compose")
    return await runner(command, cwd=str(cwd))


def _build_compose_cmd(compose_cmd: str, compose_file: Path, subcommand: str, service: str | None = None) -> str:
    cmd = f'{compose_cmd} -f "{compose_file}" {subcommand}'
    if service:
        cmd = f"{cmd} {service}"
    return cmd


@click.group()
@click.option(
    "--pods-root",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True, exists=False),
    default=None,
    envvar=PODS_ROOT_ENV,
    help=f"Root directory containing pod folders (env: {PODS_ROOT_ENV}).",
)
@click.pass_context
@tracer.Sync.decorator.call_raise
def pods(ctx: click.Context, pods_root: Path | None) -> None:
    """Manage local AI pods (list, status, build, run, down, logs)."""

    ctx.obj = PodsContext(pods_root=str(pods_root) if pods_root else None)


@pods.command("list")
@click.pass_context
@tracer.Sync.decorator.call_raise
def list_pods(ctx: click.Context) -> None:
    """List known pods and their resolved path status."""

    context = _get_context(ctx)
    try:
        root = _resolve_pods_root(context)
    except click.ClickException:
        log.info("pods_root: not found")
        log.info("No pods discovered (set --pods-root or %s).", PODS_ROOT_ENV)
        return

    log.info("pods_root: %s", root)
    specs = _discover_pod_specs(root)
    if not specs:
        log.info("No pods discovered in %s", root)
        return

    for pod in specs.values():
        pod_path = (root / pod.folder).resolve()
        status = "available" if pod_path.exists() else "missing"
        log.info("- %s: %s (%s)", pod.name, status, pod_path)


@pods.command("status")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
def status(ctx: click.Context, pod_name: str) -> None:
    """Show docker compose status for a pod."""

    context = _get_context(ctx)
    pod = _resolve_pod_spec(context, pod_name)
    pod_path = _resolve_pod_path(context, pod)
    compose_file = _compose_file(pod_path)
    command = _build_compose_cmd(_resolve_compose_command(), compose_file, "ps")
    result = asyncio.run(_run_compose(command, pod_path, stream=False))
    output = result.stdout.strip() if result.stdout.strip() else "No compose status output."
    log.info("%s", output)


@pods.command("build")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
def build(ctx: click.Context, pod_name: str) -> None:
    """Build a pod docker image."""

    context = _get_context(ctx)
    pod = _resolve_pod_spec(context, pod_name)
    if not pod.buildable:
        log.info("Pod '%s' uses prebuilt images only. Nothing to build.", pod.name)
        return

    pod_path = _resolve_pod_path(context, pod)
    compose_file = _compose_file(pod_path)
    command = _build_compose_cmd(_resolve_compose_command(), compose_file, "build", service=pod.service)
    asyncio.run(_run_compose(command, pod_path, stream=True))
    log.info("Build completed for pod '%s'.", pod.name)


@pods.command("run")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
def run_pod(ctx: click.Context, pod_name: str) -> None:
    """Start a pod in detached mode."""

    context = _get_context(ctx)
    pod = _resolve_pod_spec(context, pod_name)
    pod_path = _resolve_pod_path(context, pod)
    compose_file = _compose_file(pod_path)
    command = _build_compose_cmd(_resolve_compose_command(), compose_file, "up -d")
    asyncio.run(_run_compose(command, pod_path, stream=True))
    log.info("Pod '%s' is up.", pod.name)


@pods.command("down")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
def down_pod(ctx: click.Context, pod_name: str) -> None:
    """Stop and remove a pod stack."""

    context = _get_context(ctx)
    pod = _resolve_pod_spec(context, pod_name)
    pod_path = _resolve_pod_path(context, pod)
    compose_file = _compose_file(pod_path)
    command = _build_compose_cmd(_resolve_compose_command(), compose_file, "down")
    asyncio.run(_run_compose(command, pod_path, stream=True))
    log.info("Pod '%s' is down.", pod.name)


@pods.command("logs")
@click.argument("pod_name", type=str)
@click.option("--follow/--no-follow", default=True, show_default=True, help="Stream logs continuously.")
@click.option("--tail", default=200, show_default=True, type=int, help="Number of log lines to show.")
@click.pass_context
@tracer.Sync.decorator.call_raise
def logs(ctx: click.Context, pod_name: str, follow: bool, tail: int) -> None:
    """Show pod logs."""

    context = _get_context(ctx)
    pod = _resolve_pod_spec(context, pod_name)
    pod_path = _resolve_pod_path(context, pod)
    compose_file = _compose_file(pod_path)

    follow_flag = "-f " if follow else ""
    subcommand = f"logs {follow_flag}--tail {tail}"
    command = _build_compose_cmd(_resolve_compose_command(), compose_file, subcommand, service=pod.service)
    asyncio.run(_run_compose(command, pod_path, stream=True))
