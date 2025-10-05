"""Minimal user-space Blender download manager."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from bundle.core import data, logger, tracer, utils
from bundle.core.downloader import DownloaderTQDM
from bundle.core.platform import platform_info

log = logger.get_logger(__name__)

_BASE_URL = "https://download.blender.org"
_INSTALL_ENV = "BUNDLE_BLENDER_HOME"
_CACHE_ENV = "BUNDLE_BLENDER_CACHE"


class BlenderEnvironment(data.Data):
    blender_executable: Path
    python_executable: Path
    scripts_dir: Path

    @property
    def site_packages(self) -> Path:
        return self.scripts_dir / "modules"


def _default_install_root() -> Path:
    override = os.environ.get(_INSTALL_ENV)
    if override:
        return Path(override).expanduser()
    if platform_info.is_windows:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "TheBundle" / "blender"
    if platform_info.is_darwin:
        return Path.home() / "Library" / "Application Support" / "TheBundle" / "blender"
    if platform_info.is_linux:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / "thebundle" / "blender"
    return Path.home() / ".thebundle" / "blender"


def _default_cache_root() -> Path:
    override = os.environ.get(_CACHE_ENV)
    if override:
        return Path(override).expanduser()
    if platform_info.is_windows:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "TheBundle" / "cache" / "blender"
    if platform_info.is_darwin:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / "Library" / "Caches"))
        return base / "TheBundle" / "blender"
    if platform_info.is_linux:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "thebundle" / "blender"
    return Path.home() / ".thebundle" / "cache" / "blender"


class BlenderAppManager(data.Data):
    install_root: Path = data.Field(default_factory=_default_install_root)
    cache_root: Path = data.Field(default_factory=_default_cache_root)
    base_url: str = _BASE_URL

    def __init__(self, **data):  # type: ignore[override]
        super().__init__(**data)
        utils.ensure_path(self.install_root)
        utils.ensure_path(self.cache_root)

    def archive_name(self, version: str, arch: str | None = None) -> str:
        architecture = arch or self._architecture()
        sys_name = platform_info.system
        if sys_name == "windows":
            return f"blender-{version}-windows-{architecture}.zip"
        if sys_name == "linux":
            return f"blender-{version}-linux-{architecture}.tar.xz"
        if sys_name == "darwin":
            return f"blender-{version}-macos-{architecture}.dmg"
        raise RuntimeError(f"Unsupported system: {sys_name}")

    def archive_url(self, version: str, channel: str = "release", arch: str | None = None) -> str:
        directory = self._release_dir(version, channel)
        return f"{self.base_url}/{directory}/{self.archive_name(version, arch)}"

    def cache_path(self, version: str, channel: str = "release", arch: str | None = None) -> Path:
        return self.cache_root / channel / version / self.archive_name(version, arch)

    @property
    def default_version(self) -> str:
        versions = sorted(self.installed_versions(), key=lambda path: path.name)
        return versions[-1].name if versions else "4.5.0"

    def installed_versions(self) -> list[Path]:
        if not self.install_root.exists():
            return []
        return [p for p in self.install_root.iterdir() if p.is_dir()]

    def managed_environments(self) -> list[runtime_env.BlenderEnvironment]:
        from ..runtime import env as runtime_env

        environments: list[runtime_env.BlenderEnvironment] = []
        for install_dir in sorted(self.installed_versions(), key=lambda path: path.name, reverse=True):
            env = runtime_env.resolve_environment_from_install(install_dir)
            if env:
                environments.append(env)
        return environments

    def default_environment(self) -> runtime_env.BlenderEnvironment | None:
        envs = self.managed_environments()
        return envs[0] if envs else None

    @tracer.Async.decorator.call_raise
    async def ensure_download(
        self, version: str, channel: str = "release", arch: str | None = None, force: bool = False
    ) -> Path:
        cache_file = self.cache_path(version, channel, arch)
        if cache_file.exists() and not force:
            log.info("Using cached archive: %s", cache_file)
            return cache_file
        utils.ensure_path(cache_file.parent)
        url = self.archive_url(version, channel, arch)
        log.info("Downloading %s", url)
        downloader = DownloaderTQDM(url=url, destination=cache_file)
        if not await downloader.download():
            raise RuntimeError(f"Download failed: {url}")
        return cache_file

    @tracer.Async.decorator.call_raise
    async def ensure_install(
        self, version: str, channel: str = "release", arch: str | None = None, force: bool = False
    ) -> Path:
        target = self.install_root / version
        if target.exists() and not force:
            log.info("Blender %s already available at %s", version, target)
            return target

        archive = await self.ensure_download(version, channel, arch, force)
        if target.exists():
            shutil.rmtree(target)
        utils.ensure_path(target.parent)
        tmp = target.with_suffix(".partial")
        if tmp.exists():
            shutil.rmtree(tmp)

        shutil.unpack_archive(str(archive), str(tmp))
        extracted = _single_dir(tmp) or tmp
        shutil.move(str(extracted), str(target))
        shutil.rmtree(tmp, ignore_errors=True)
        log.info("Installed Blender %s into %s", version, target)
        return target

    def _architecture(self) -> str:
        arch = platform_info.arch.lower()
        if platform_info.is_windows:
            return "x64"
        if platform_info.is_linux:
            return "arm64" if "arm" in arch else "x64"
        if platform_info.is_darwin:
            return "arm64" if "arm" in arch or "aarch" in arch else "x64"
        return arch

    def _release_dir(self, version: str, channel: str) -> str:
        major_minor = ".".join(version.split(".")[:2])
        if channel == "release":
            return f"release/Blender{major_minor}"
        if channel == "lts":
            return f"release/BlenderLTS/{major_minor}"
        raise ValueError(f"Unsupported channel: {channel}")


def _single_dir(path: Path) -> Path | None:
    dirs = [item for item in path.iterdir() if item.is_dir()]
    return dirs[0] if len(dirs) == 1 else None
