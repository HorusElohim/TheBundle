"""CLI for Lambda Labs cloud GPU management."""

from __future__ import annotations

from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.table import Table

from bundle.core import logger, tracer

from .client import LambdaClient
from .config import LambdaLabsConfig

log = logger.get_logger(__name__)
console = Console()


def _get_client(api_key: str | None = None) -> tuple[LambdaClient, str]:
    cfg = LambdaLabsConfig.load()
    key = api_key or cfg.api_key
    if not key:
        raise click.ClickException("No API key configured. Run: bundle lambdalabs setup --api-key YOUR_KEY")
    return LambdaClient(key), key


@click.group(name="lambdalabs")
@tracer.Sync.decorator.call_raise
async def lambdalabs():
    """Lambda Labs cloud GPU — launch, manage, and run remote jobs."""
    pass


# ---------------------------------------------------------------------------
# bundle lambdalabs setup
# ---------------------------------------------------------------------------


@lambdalabs.command()
@click.option("--api-key", required=True, envvar="LAMBDA_API_KEY", help="Lambda Labs API key.")
@click.option("--ssh-key", default="", help="Default SSH key name in your Lambda account.")
@click.option("--region", default="us-east-1", help="Default region.")
@click.option("--instance-type", default="gpu_1x_a10", help="Default instance type.")
@click.option("--filesystem", default="", help="Default filesystem name (persistent NFS for datasets/results).")
@tracer.Sync.decorator.call_raise
async def setup(api_key: str, ssh_key: str, region: str, instance_type: str, filesystem: str):
    """Save API key and defaults to ~/.bundle/lambdalabs.json."""
    cfg = LambdaLabsConfig(
        api_key=api_key,
        default_ssh_key=ssh_key,
        default_region=region,
        default_instance_type=instance_type,
        default_filesystem=filesystem,
    )
    cfg.save()
    log.info("Lambda Labs config saved to ~/.bundle/lambdalabs.json")
    log.info("  API key: %s...%s", api_key[:4], api_key[-4:])
    if ssh_key:
        log.info("  Default SSH key: %s", ssh_key)
    if filesystem:
        log.info("  Default filesystem: %s", filesystem)


# ---------------------------------------------------------------------------
# bundle lambdalabs types
# ---------------------------------------------------------------------------


@lambdalabs.command()
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def types(api_key: str | None):
    """List available GPU instance types and prices."""
    client, _ = _get_client(api_key)
    async with client:
        instance_types = await client.instance_types()

    table = Table(title="Lambda Labs Instance Types")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("vCPUs", justify="right")
    table.add_column("RAM (GiB)", justify="right")
    table.add_column("Storage (GiB)", justify="right")
    table.add_column("$/hr", justify="right", style="green")

    for name, it in sorted(instance_types.items()):
        table.add_row(
            name,
            it.description,
            str(it.specs.vcpus),
            str(it.specs.memory_gib),
            str(it.specs.storage_gib),
            f"${it.price_per_hour:.2f}",
        )
    console.print(table)


# ---------------------------------------------------------------------------
# bundle lambdalabs instances
# ---------------------------------------------------------------------------


@lambdalabs.group()
@tracer.Sync.decorator.call_raise
async def instances():
    """Manage Lambda Labs instances."""
    pass


@instances.command(name="list")
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def instances_list(api_key: str | None):
    """List all active instances."""
    client, _ = _get_client(api_key)
    async with client:
        active = await client.instances()

    if not active:
        log.info("No active instances.")
        return

    table = Table(title="Active Lambda Labs Instances")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Status", style="yellow")
    table.add_column("IP")
    table.add_column("SSH Keys")

    for inst in active:
        table.add_row(
            inst.id[:12] + "…",
            inst.name or "—",
            inst.instance_type.name,
            inst.status.value,
            inst.ip or "—",
            ", ".join(inst.ssh_key_names) or "—",
        )
    console.print(table)


@instances.command(name="launch")
@click.option("--type", "instance_type", default=None, help="Instance type (e.g. gpu_1x_a10).")
@click.option("--key", "ssh_key_name", default=None, help="SSH key name in your Lambda account.")
@click.option("--region", default=None, help="Region (e.g. us-east-1).")
@click.option("--name", default=None, help="Instance name.")
@click.option("--filesystem", default=None, help="Filesystem name to mount (persistent NFS).")
@click.option("--wait/--no-wait", default=True, help="Wait until instance is active.")
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def instances_launch(
    instance_type: str | None,
    ssh_key_name: str | None,
    region: str | None,
    name: str | None,
    filesystem: str | None,
    wait: bool,
    api_key: str | None,
):
    """Launch a new GPU instance."""
    cfg = LambdaLabsConfig.load()
    key = api_key or cfg.api_key
    if not key:
        raise click.ClickException("No API key — run: bundle lambdalabs setup --api-key KEY")

    selected_type = instance_type or cfg.default_instance_type
    ssh_key = ssh_key_name or cfg.default_ssh_key
    reg = region or cfg.default_region
    fs = filesystem or cfg.default_filesystem

    if not ssh_key:
        raise click.ClickException("No SSH key — specify --key or set default via: bundle lambdalabs setup --ssh-key NAME")

    async with LambdaClient(key) as client:
        ids = await client.launch(
            instance_type_name=selected_type,
            ssh_key_names=[ssh_key],
            region_name=reg,
            name=name,
            file_system_names=[fs] if fs else [],
        )
        if not ids:
            raise click.ClickException("Launch failed — no instance IDs returned")
        log.info("Launched instance: %s", ids[0])

        if wait:
            instance = await client.wait_active(ids[0])
            log.info("Instance ready: %s @ %s", instance.id[:12], instance.ip)
            log.info("Connect: ssh ubuntu@%s", instance.ip)
        else:
            log.info("Instance ID: %s (use 'bundle lambdalabs instances list' to check status)", ids[0])


@instances.command(name="terminate")
@click.argument("instance_id")
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@tracer.Sync.decorator.call_raise
async def instances_terminate(instance_id: str, api_key: str | None, yes: bool):
    """Terminate an instance by ID."""
    if not yes:
        click.confirm(f"Terminate instance {instance_id}?", abort=True)
    client, _ = _get_client(api_key)
    async with client:
        terminated = await client.terminate([instance_id])
    log.info("Terminated: %s", terminated)


# ---------------------------------------------------------------------------
# bundle lambdalabs keys
# ---------------------------------------------------------------------------


@lambdalabs.group()
@tracer.Sync.decorator.call_raise
async def keys():
    """Manage SSH keys in your Lambda Labs account."""
    pass


@keys.command(name="list")
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def keys_list(api_key: str | None):
    """List SSH keys in your account."""
    client, _ = _get_client(api_key)
    async with client:
        ssh_keys = await client.ssh_keys()

    if not ssh_keys:
        log.info("No SSH keys in account.")
        return

    table = Table(title="SSH Keys")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Public Key (prefix)")

    for k in ssh_keys:
        table.add_row(k.id[:12] + "…", k.name, k.public_key[:60] + "…")
    console.print(table)


@keys.command(name="add")
@click.option("--name", required=True, help="Key name in Lambda account.")
@click.option(
    "--pub-key",
    "pub_key_path",
    type=click.Path(path_type=Path),
    default=Path.home() / ".ssh" / "id_rsa.pub",
    help="Path to public key file.",
)
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def keys_add(name: str, pub_key_path: Path, api_key: str | None):
    """Add an SSH public key to your Lambda account."""
    if not pub_key_path.exists():
        raise click.ClickException(f"Public key not found: {pub_key_path}")
    public_key = pub_key_path.read_text().strip()
    client, _ = _get_client(api_key)
    async with client:
        key = await client.add_ssh_key(name=name, public_key=public_key)
    log.info("Added SSH key: %s (id: %s)", key.name, key.id[:12])


# ---------------------------------------------------------------------------
# bundle lambdalabs filesystems
# ---------------------------------------------------------------------------


@lambdalabs.group()
@tracer.Sync.decorator.call_raise
async def filesystems():
    """Manage Lambda Labs persistent filesystems (NFS, survives instance termination)."""
    pass


@filesystems.command(name="list")
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def filesystems_list(api_key: str | None):
    """List all filesystems in your account."""
    client, _ = _get_client(api_key)
    async with client:
        fss = await client.filesystems()

    if not fss:
        log.info("No filesystems found. Create one with: bundle lambdalabs filesystems create --name NAME")
        return

    table = Table(title="Lambda Labs Filesystems")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Region")
    table.add_column("Mount path on instance")

    for fs in fss:
        region_name = fs.region.get("name", "—") if isinstance(fs.region, dict) else str(fs.region)
        table.add_row(fs.id[:12] + "…", fs.name, region_name, str(fs.path))
    console.print(table)


@filesystems.command(name="create")
@click.option("--name", required=True, help="Filesystem name.")
@click.option("--region", default=None, help="Region (defaults to configured default).")
@click.option("--set-default/--no-set-default", default=True, help="Save as default filesystem in config.")
@click.option("--api-key", default=None, envvar="LAMBDA_API_KEY")
@tracer.Sync.decorator.call_raise
async def filesystems_create(name: str, region: str | None, set_default: bool, api_key: str | None):
    """Create a new persistent filesystem."""
    cfg = LambdaLabsConfig.load()
    key = api_key or cfg.api_key
    if not key:
        raise click.ClickException("No API key — run: bundle lambdalabs setup --api-key KEY")
    reg = region or cfg.default_region

    async with LambdaClient(key) as client:
        fs = await client.create_filesystem(name=name, region_name=reg)

    log.info("Created filesystem: %s (id: %s)", fs.name, fs.id[:12])
    log.info("  Mount path on instances: %s", fs.path)

    if set_default:
        cfg = LambdaLabsConfig.load()
        updated = cfg.model_copy(update={"default_filesystem": fs.name})
        updated.save()
        log.info("  Saved as default filesystem in ~/.bundle/lambdalabs.json")


# ---------------------------------------------------------------------------
# bundle lambdalabs quickstart
# ---------------------------------------------------------------------------


@lambdalabs.command()
@tracer.Sync.decorator.call_raise
async def quickstart():
    """Interactive guided setup: from zero to a running GPU instance.

    Walks you through:
        1. Creating a Lambda Labs account
        2. Generating an API key
        3. Saving config locally
        4. Adding your SSH key
        5. Choosing and launching an instance type
        6. Connecting via SSH
    """
    console.print("\n[bold cyan]Lambda Labs Quickstart[/bold cyan]")
    console.print("=" * 50)

    console.print("""
[bold]Step 1 — Create your Lambda Labs account[/bold]

  Open https://cloud.lambdalabs.com/sign-up in your browser.
  Complete registration and verify your email.
  Add a payment method under Billing → Payment methods.
""")
    click.pause("Press Enter when your account is ready...")

    console.print("""
[bold]Step 2 — Generate an API key[/bold]

  Go to: https://cloud.lambdalabs.com/api-keys
  Click "Generate API key", give it a name (e.g. "bundle"),
  and copy the key. You will only see it once.
""")
    api_key = click.prompt("Paste your API key here", hide_input=True)

    console.print("""
[bold]Step 3 — Add your SSH public key[/bold]

  Go to: https://cloud.lambdalabs.com/ssh-keys
  Or let us add it now.
""")
    pub_key_path = Path.home() / ".ssh" / "id_rsa.pub"
    key_name = ""
    if click.confirm(f"Add {pub_key_path} to your Lambda account?", default=True):
        if not pub_key_path.exists():
            console.print(f"[yellow]No key at {pub_key_path}. Generate one with: ssh-keygen -t rsa[/yellow]")
        else:
            key_name = click.prompt("Name for this SSH key in Lambda", default="bundle-key")
            async with LambdaClient(api_key) as client:
                key = await client.add_ssh_key(key_name, pub_key_path.read_text().strip())
            log.info("SSH key added: %s", key.name)

    console.print("\n[bold]Step 4 — Choose an instance type[/bold]\n")
    async with LambdaClient(api_key) as client:
        itypes = await client.instance_types()

    table = Table()
    table.add_column("#", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("$/hr", justify="right", style="green")

    type_list = sorted(itypes.items())
    for i, (name, it) in enumerate(type_list, 1):
        table.add_row(str(i), name, it.description, f"${it.price_per_hour:.2f}")
    console.print(table)

    choice = click.prompt("Select instance number", type=int, default=1)
    selected_type = type_list[choice - 1][0]

    console.print("\n[bold]Step 5 — Persistent filesystem (recommended)[/bold]")
    console.print("""
  A filesystem stores your datasets and results across jobs.
  Images and SfM output are uploaded once and reused — no re-uploading.
  The filesystem survives instance termination and costs ~$0.20/GiB/month.
""")
    fs_name = ""
    if click.confirm("Create a persistent filesystem now?", default=True):
        fs_name = click.prompt("Filesystem name", default="bundle-recon3d")
        async with LambdaClient(api_key) as client:
            fs = await client.create_filesystem(name=fs_name, region_name="us-east-1")
        log.info("Filesystem created: %s — mounted at %s on instances", fs.name, fs.path)

    console.print("\n[bold]Step 6 — Saving config[/bold]")
    cfg = LambdaLabsConfig(
        api_key=api_key,
        default_ssh_key=key_name,
        default_instance_type=selected_type,
        default_filesystem=fs_name,
    )
    cfg.save()
    log.info("Config saved to ~/.bundle/lambdalabs.json")

    if click.confirm(f"\nLaunch a {selected_type} instance now?", default=False):
        name = click.prompt("Instance name", default="bundle-quickstart")
        async with LambdaClient(api_key) as client:
            ids = await client.launch(
                instance_type_name=selected_type,
                ssh_key_names=[key_name],
                name=name,
            )
            log.info("Launched: %s — waiting for active...", ids[0])
            instance = await client.wait_active(ids[0])

        console.print("\n[bold green]Instance ready![/bold green]")
        console.print(f"  ID:  {instance.id}")
        console.print(f"  IP:  {instance.ip}")
        console.print(f"\nConnect with:  [cyan]ssh ubuntu@{instance.ip}[/cyan]")
        console.print(f"Terminate with: [cyan]bundle lambdalabs instances terminate {instance.id}[/cyan]")
    else:
        console.print("\nWhen you're ready, launch with:")
        console.print(f"  [cyan]bundle lambdalabs instances launch --type {selected_type}[/cyan]")

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("Run Gaussian training on Lambda:")
    console.print("  [cyan]bundle recon3d run --workspace ./ws --lambda[/cyan]\n")
