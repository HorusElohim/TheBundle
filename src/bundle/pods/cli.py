from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table

from bundle.core import logger, tracer

from .manager import PODS_ROOT_ENV, PodManager

log = logger.get_logger(__name__)


def _get_manager(ctx: click.Context) -> PodManager:
    """Retrieve the PodManager instance stored in the Click context."""
    return ctx.obj


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
    """Manage local AI pods (list, status, build, run, up, down, logs)."""
    ctx.obj = PodManager.create(pods_root)


@pods.command("list")
@click.pass_context
@tracer.Sync.decorator.call_raise
async def list_pods(ctx: click.Context) -> None:
    """List known pods and their resolved path status."""
    mgr = _get_manager(ctx)
    if not mgr.specs:
        log.info("No pods discovered in %s", mgr.pods_root)
        return

    running = await mgr.running_containers()

    table = Table(title=f"Pods  [{mgr.pods_root}]", title_style="bold cyan")
    table.add_column("Pod", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Containers")
    table.add_column("Path", style="dim")

    for pod in mgr.specs.values():
        pod_path = (mgr.pods_root / pod.folder).resolve()
        if not pod_path.exists():
            status_text = "[red]missing[/red]"
        elif pod.containers and all(c in running for c in pod.containers):
            status_text = "[green]running[/green]"
        elif pod.containers and any(c in running for c in pod.containers):
            status_text = "[yellow]partial[/yellow]"
        else:
            status_text = "[dim]stopped[/dim]"

        container_parts = []
        for c in pod.containers:
            if c in running:
                container_parts.append(f"[green]{c}[/green]")
            else:
                container_parts.append(f"[dim]{c}[/dim]")
        containers_text = "\n".join(container_parts) if container_parts else "[dim]-[/dim]"

        table.add_row(pod.name, status_text, containers_text, str(pod_path))

    Console().print(table)


@pods.command("status")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
async def status(ctx: click.Context, pod_name: str) -> None:
    """Show docker compose status for a pod."""
    mgr = _get_manager(ctx)
    pod = mgr.get(pod_name)
    result = await mgr.status(pod)
    output = result.stdout.strip() if result.stdout.strip() else "No compose status output."
    log.info("%s", output)


@pods.command("build")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
async def build(ctx: click.Context, pod_name: str) -> None:
    """Build a pod docker image."""
    mgr = _get_manager(ctx)
    pod = mgr.get(pod_name)
    await mgr.build(pod)
    log.info("Build completed for pod '%s'.", pod.name)


@pods.command("run")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
async def run_pod(ctx: click.Context, pod_name: str) -> None:
    """Start a pod in detached mode."""
    mgr = _get_manager(ctx)
    pod = mgr.get(pod_name)
    await mgr.run(pod)
    log.info("Pod '%s' is up.", pod.name)


@pods.command("up")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
async def up(ctx: click.Context, pod_name: str) -> None:
    """Start a pod and stream its logs."""
    mgr = _get_manager(ctx)
    pod = mgr.get(pod_name)
    await mgr.run(pod)
    log.info("Pod '%s' is up. Streaming logs...", pod.name)
    await mgr.logs(pod, follow=True, tail=200)


@pods.command("down")
@click.argument("pod_name", type=str)
@click.pass_context
@tracer.Sync.decorator.call_raise
async def down_pod(ctx: click.Context, pod_name: str) -> None:
    """Stop and remove a pod stack."""
    mgr = _get_manager(ctx)
    pod = mgr.get(pod_name)
    await mgr.down(pod)
    log.info("Pod '%s' is down.", pod.name)


@pods.command("logs")
@click.argument("pod_name", type=str)
@click.option("--follow/--no-follow", default=True, show_default=True, help="Stream logs continuously.")
@click.option("--tail", default=200, show_default=True, type=int, help="Number of log lines to show.")
@click.pass_context
@tracer.Sync.decorator.call_raise
async def logs(ctx: click.Context, pod_name: str, follow: bool, tail: int) -> None:
    """Show pod logs."""
    mgr = _get_manager(ctx)
    pod = mgr.get(pod_name)
    await mgr.logs(pod, follow=follow, tail=tail)
