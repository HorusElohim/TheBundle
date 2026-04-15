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


def test_pick_latest_series() -> None:
    html = """
    <a href="Blender3.6/">Blender3.6/</a>
    <a href="Blender4.5/">Blender4.5/</a>
    <a href="Blender5.0/">Blender5.0/</a>
    <a href="Blender5.1/">Blender5.1/</a>
    """
    assert BlenderAppManager._pick_latest_series(html) == (5, 1)


def test_pick_latest_patch() -> None:
    html = """
    blender-5.1.0-linux-x64.tar.xz
    blender-5.1.1-linux-x64.tar.xz
    blender-5.1.1-macos-arm64.dmg
    blender-4.5.3-linux-x64.tar.xz
    """
    assert BlenderAppManager._pick_latest_patch(html, 5, 1) == "5.1.1"
    assert BlenderAppManager._pick_latest_patch(html, 4, 5) == "4.5.3"


def test_pick_latest_patch_missing_series() -> None:
    with pytest.raises(RuntimeError, match="No Blender 9.9.x archives"):
        BlenderAppManager._pick_latest_patch("blender-5.1.0-linux-x64.tar.xz", 9, 9)


def test_pick_latest_series_empty() -> None:
    with pytest.raises(RuntimeError, match="No Blender series"):
        BlenderAppManager._pick_latest_series("<html>no links</html>")
