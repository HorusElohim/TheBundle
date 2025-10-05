"""CLI entrypoints for bundle.blender."""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Iterable

import rich_click as click

from bundle.core import logger, process, tracer
from bundle.core.platform import platform_info

from .app.manager import BlenderAppManager
from .runtime import (
    BlenderEnvironment,
    discover_default_environment,
    managed_environments,
    resolve_environment_from_python,
)

log = logger.get_logger(__name__)


def _detect_project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in current.parents:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return current.parents[3]


PROJECT_ROOT = _detect_project_root()
DEFAULT_PACKAGE_PATH = PROJECT_ROOT


def _format_command(parts: Iterable[Path | str]) -> str:
    items = [str(part) for part in parts]
    return subprocess.list2cmdline(items) if platform_info.is_windows else shlex.join(items)


async def _run_python_command(python_executable: Path, args: list[str]) -> process.ProcessResult:
    command = _format_command([python_executable, *args])
    log.info("Executing: %s", command)
    return await process.Process()(command)


async def _discover_site_packages(
    python_executable: Path,
    env_info: BlenderEnvironment | None,
) -> Path:
    if env_info is not None:
        return env_info.site_packages

    code = "import json, site; print(json.dumps(site.getsitepackages()))"
    result = await _run_python_command(python_executable, ["-c", code])
    payload = result.stdout.strip().splitlines()[-1] if result.stdout else ""
    if not payload:
        raise click.ClickException("Unable to determine site-packages via Python")
    try:
        candidates = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise click.ClickException(f"Unexpected site-packages output: {payload}") from exc
    if not candidates:
        raise click.ClickException("Python reported no site-packages directories")
    return Path(candidates[0])


def _compute_python_hint(install_dir: Path, version: str) -> Path | None:
    major_minor = ".".join(version.split(".")[:2])
    roots = [
        install_dir / major_minor / "python",
        install_dir / "Resources" / major_minor / "python",
        install_dir / "Blender.app" / "Contents" / "Resources" / major_minor / "python",
    ]
    for root in roots:
        if not root.exists():
            continue
        pattern = "**/python*.exe" if platform_info.is_windows else "**/python3*"
        candidates = sorted(root.glob(pattern))
        if candidates:
            return candidates[0]
    return None


@click.group()
@tracer.Sync.decorator.call_raise
async def blender() -> None:
    """Manage Blender integrations for TheBundle."""
    log.debug("bundle blender CLI initialised")


@blender.command("download")
@tracer.Sync.decorator.call_raise
@click.option("--version", "version", default=None, help="Blender version to download (e.g. 4.5.0).")
@click.option("--channel", type=click.Choice(["release", "lts"], case_sensitive=False), default="release", show_default=True)
@click.option(
    "--dest",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=None,
    help="Target directory for managed installs.",
)
@click.option("--arch", type=click.Choice(["auto", "x64", "arm64"], case_sensitive=False), default="auto", show_default=True)
@click.option("--force", is_flag=True, default=False, help="Re-download and overwrite existing archives/installations.")
async def download(version: str | None, channel: str, dest: str | None, arch: str, force: bool) -> None:
    if dest is not None:
        manager = BlenderAppManager(install_root=Path(dest))
    else:
        manager = BlenderAppManager()
    chosen_version = version or manager.default_version
    chosen_arch = None if arch.lower() == "auto" else arch.lower()

    install_dir = await manager.ensure_install(
        version=chosen_version,
        channel=channel.lower(),
        arch=chosen_arch,
        force=force,
    )
    log.info("Blender %s installed at %s", chosen_version, install_dir)
    python_hint = _compute_python_hint(install_dir, chosen_version)
    if python_hint:
        log.info("Blender Python hint: %s", python_hint)
    log.info("Set BUNDLE_BLENDER_PYTHON to %s if discovery needs help", python_hint or install_dir)


@blender.command("info")
@tracer.Sync.decorator.call_raise
async def info() -> None:
    """Show detected Blender environment details."""
    managed_envs = managed_environments()

    try:
        default_env = await discover_default_environment()
    except FileNotFoundError:
        default_env = None

    def _display(label: str, env_obj: BlenderEnvironment) -> None:
        log.info(f"{label}:")
        log.info("  blender: %s", env_obj.blender_executable)
        log.info("  python : %s", env_obj.python_executable)
        log.info("  scripts: %s", env_obj.scripts_dir)
        log.info("  site   : %s", env_obj.site_packages)

    seen: set[Path] = set()
    if default_env:
        _display("Default environment", default_env)
        seen.add(default_env.scripts_dir)
    else:
        log.warning("Default environment not found")

    for idx, env_obj in enumerate(managed_envs, 1):
        if env_obj.scripts_dir in seen:
            continue
        label = "Managed install" if len(managed_envs) == 1 else f"Managed install #{idx}"
        _display(label, env_obj)
        seen.add(env_obj.scripts_dir)

    if not managed_envs:
        manager = BlenderAppManager()
        log.info("No managed Blender installs found under %s", manager.install_root)


@blender.command("install")
@tracer.Sync.decorator.call_raise
@click.option(
    "--python", "python_executable", type=click.Path(path_type=str, exists=True, dir_okay=False, file_okay=True), default=None
)
@click.option(
    "--package-path",
    type=click.Path(path_type=str, exists=True, file_okay=False, dir_okay=True),
    default=str(DEFAULT_PACKAGE_PATH),
    show_default=True,
)
@click.option("--upgrade-pip/--no-upgrade-pip", default=True, show_default=True)
async def install(
    python_executable: str | None,
    package_path: str,
    upgrade_pip: bool,
) -> None:
    env_info: BlenderEnvironment | None = None
    if python_executable:
        python_path = Path(python_executable)
        env_info = resolve_environment_from_python(python_path)
        if env_info:
            log.info("Using Blender environment override: %s", env_info.blender_executable)
    else:
        env_info = await discover_default_environment()
        python_path = env_info.python_executable
        log.info("Using discovered Blender Python: %s", python_path)

    if not python_path.exists():
        raise click.ClickException(f"Python interpreter not found: {python_path}")

    site_packages = await _discover_site_packages(python_path, env_info)
    site_packages.mkdir(parents=True, exist_ok=True)
    log.info("Installing into Blender site-packages: %s", site_packages)

    package_root = Path(package_path)
    if not (package_root / "pyproject.toml").exists():
        raise click.ClickException(f"Package root does not contain pyproject.toml: {package_root}")

    if upgrade_pip:
        await _run_python_command(python_path, ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    await _run_python_command(
        python_path,
        [
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--target",
            str(site_packages),
            str(package_root),
        ],
    )
    log.info("Installation complete: bundle available inside Blender Python")
