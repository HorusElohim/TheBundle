"""Runtime helpers for discovering Blender installations."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from bundle.core import logger, tracer
from bundle.core.platform import platform_info

from ..app.manager import BlenderAppManager, BlenderEnvironment

log = logger.get_logger(__name__)

_ENV_EXECUTABLE = "BUNDLE_BLENDER_EXECUTABLE"
_ENV_PYTHON = "BUNDLE_BLENDER_PYTHON"
_ENV_ROOT = "BUNDLE_BLENDER_ROOT"
_VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")


class BlenderRuntime:
    """Centralises knowledge about Blender environments on the host machine."""

    def __init__(self, manager: BlenderAppManager | None = None) -> None:
        self.manager = manager or BlenderAppManager()

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def managed_environments(self) -> list[BlenderEnvironment]:
        paths = sorted(self.manager.installed_versions(), key=lambda path: path.name, reverse=True)
        return [env for path in paths if (env := self.from_install(path))]

    def env_var_environments(self) -> list[BlenderEnvironment]:
        results: list[BlenderEnvironment] = []
        python_path = _existing(os.environ.get(_ENV_PYTHON))
        executable = _existing(os.environ.get(_ENV_EXECUTABLE))
        install_root = _existing(os.environ.get(_ENV_ROOT))

        if python_path and (env := self.from_python(python_path, executable)):
            results.append(env)
        if executable and (env := self.from_install(executable.parent)):
            results.append(env)
        if install_root and (env := self.from_install(install_root)):
            results.append(env)
        return results

    def system_environments(self) -> list[BlenderEnvironment]:
        results = [env for root in _platform_candidates() if (env := self.from_install(root))]
        system_env = self._from_system_path()
        if system_env:
            results.append(system_env)
        return results

    @tracer.Async.decorator.call_raise
    async def discover_default(self) -> BlenderEnvironment:
        managed = self.managed_environments()
        if managed:
            return managed[0]
        for env in self.iter_environments():
            return env
        raise FileNotFoundError(
            "Unable to locate a Blender installation automatically. "
            "Set BUNDLE_BLENDER_PYTHON or run `bundle blender download`."
        )

    def iter_environments(self) -> list[BlenderEnvironment]:
        ordered = self.env_var_environments() + self.managed_environments() + self.system_environments()
        unique: list[BlenderEnvironment] = []
        seen: set[Path] = set()
        for env in ordered:
            key = env.scripts_dir
            if key in seen:
                continue
            seen.add(key)
            unique.append(env)
        return unique

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def from_install(self, install_root: Path) -> BlenderEnvironment | None:
        candidate = _normalise_root(install_root)
        if not candidate:
            return None
        blender = _blender_binary(candidate)
        version_dir = _version_dir(candidate)
        if not blender or not version_dir:
            return None
        scripts = version_dir / "scripts"
        python = _python_binary(version_dir)
        if not scripts.exists() or python is None:
            return None
        return BlenderEnvironment(blender_executable=blender, python_executable=python, scripts_dir=scripts)

    def from_python(self, python_path: Path, executable_override: Path | None = None) -> BlenderEnvironment | None:
        if not python_path.exists():
            return None
        version_dir = _find_version_from_python(python_path)
        if version_dir is None:
            return None
        scripts = version_dir / "scripts"
        if not scripts.exists():
            return None
        blender = executable_override or _blender_binary(version_dir.parent)
        if blender is None:
            return None
        return BlenderEnvironment(blender_executable=blender, python_executable=python_path, scripts_dir=scripts)

    def _from_system_path(self) -> BlenderEnvironment | None:
        executable = shutil.which("blender")
        if not executable:
            return None
        return self.from_install(Path(executable).resolve().parent)


_RUNTIME = BlenderRuntime()


def runtime() -> BlenderRuntime:
    return _RUNTIME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _platform_candidates() -> list[Path]:
    if platform_info.is_windows:
        env_vars = ["PROGRAMFILES", "PROGRAMFILES(X86)"]
        return [Path(os.environ[var]) / "Blender Foundation" for var in env_vars if os.environ.get(var)]
    if platform_info.is_darwin:
        return [Path("/Applications"), Path.home() / "Applications"]
    return [Path("/usr/local/share/blender")]


def _normalise_root(path: Path) -> Path | None:
    current = path.parent if path.is_file() else path
    if not current.exists():
        return None
    if platform_info.is_darwin and current.suffix == ".app":
        return current / "Contents"
    if (current / "blender.exe").exists() or (current / "blender").exists():
        return current
    children = [child for child in current.iterdir() if child.is_dir()]
    return _normalise_root(children[0]) if len(children) == 1 else None


def _blender_binary(path: Path) -> Path | None:
    if platform_info.is_windows:
        candidate = path / "blender.exe"
    elif platform_info.is_darwin:
        candidate = (
            path / "MacOS" / "Blender" if path.name == "Contents" else path / "Blender.app" / "Contents" / "MacOS" / "Blender"
        )
    else:
        candidate = path / "blender"
    return candidate if candidate.exists() else None


def _version_dir(path: Path) -> Path | None:
    dirs = [item for item in path.iterdir() if item.is_dir() and _VERSION_RE.match(item.name)]
    return max(dirs, default=None, key=lambda p: p.name)


def _python_binary(version_dir: Path) -> Path | None:
    python_root = version_dir / "python"
    candidates = [python_root / "bin" / name for name in ("python.exe", "python3", "python")]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for candidate in python_root.glob("**/python*"):
        if candidate.is_file():
            return candidate
    return None


def _find_version_from_python(python_path: Path) -> Path | None:
    for parent in python_path.parents:
        if (parent / "scripts").exists():
            return parent
    return None


def _existing(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.exists():
        log.warning("Configured path does not exist: %s", path)
        return None
    return path
