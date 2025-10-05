from pathlib import Path

import pytest

from bundle.blender.app.manager import BlenderAppManager
from bundle.core.platform import platform_info


@pytest.fixture()
def manager(tmp_path: Path) -> BlenderAppManager:
    return BlenderAppManager(install_root=tmp_path / "install", cache_root=tmp_path / "cache", base_url="https://example.com")


def test_archive_and_url(manager: BlenderAppManager) -> None:
    arch = manager._architecture()  # type: ignore[attr-defined]
    name = manager.archive_name("4.5.0", arch)
    if platform_info.is_windows:
        assert name == "blender-4.5.0-windows-x64.zip"
        directory = "release/Blender4.5"
    elif platform_info.is_linux:
        suffix = "arm64" if arch == "arm64" else "x64"
        assert name == f"blender-4.5.0-linux-{suffix}.tar.xz"
        directory = "release/Blender4.5"
    elif platform_info.is_darwin:
        assert name == f"blender-4.5.0-macos-{arch}.dmg"
        directory = "release/Blender4.5"
    else:  # pragma: no cover
        pytest.skip("Unsupported platform")

    url = manager.archive_url("4.5.0", arch=arch)
    assert url == f"https://example.com/{directory}/{name}"


def test_cache_and_default_version(manager: BlenderAppManager) -> None:
    cache = manager.cache_path("4.5.0")
    assert cache == manager.cache_root / "release" / "4.5.0" / manager.archive_name("4.5.0")

    assert manager.default_version == "4.5.0"
    (manager.install_root / "4.0.0").mkdir(parents=True, exist_ok=True)
    (manager.install_root / "4.2.0").mkdir(parents=True, exist_ok=True)
    assert manager.default_version == "4.2.0"
