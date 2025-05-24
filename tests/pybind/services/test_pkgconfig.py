from pathlib import Path

import pytest

from bundle.core import process
from bundle.pybind.resolved.pkgconfig import PkgConfigResolved
from bundle.pybind.services.pkgconfig import PkgConfigService
from bundle.pybind.specs.pkgconfig import PkgConfigSpec

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pkg_config_service():
    return PkgConfigService()


@pytest.fixture
def pkgconfig_dir(tmp_path):
    pc_dir = tmp_path / "pkgconfig"
    pc_dir.mkdir()
    return pc_dir


@pytest.fixture
def foo_pc_file(pkgconfig_dir):
    pc_file = pkgconfig_dir / "foo.pc"
    pc_file.write_text(
        """
prefix=/usr/local
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: foo
Description: Fake foo library
Version: 1.0.0
Cflags: -I${includedir}/foo -DFOO=1
Libs: -L${libdir} -lfoo -lm
"""
    )
    return pc_file


@pytest.fixture
def bar_pc_file(pkgconfig_dir):
    pc_file = pkgconfig_dir / "bar.pc"
    pc_file.write_text(
        """
prefix=/opt/bar
exec_prefix=${prefix}
libdir=${exec_prefix}/lib
includedir=${prefix}/include

Name: bar
Description: Fake bar library
Version: 2.0.0
Cflags: -I${includedir}/bar
Libs: -L${libdir} -lbar
"""
    )
    return pc_file


@pytest.fixture
def set_pkg_config_path(pkgconfig_dir, monkeypatch):
    monkeypatch.setenv("PKG_CONFIG_PATH", str(pkgconfig_dir))
    yield


@pytest.mark.parametrize(
    "spec_kwargs",
    [
        {"packages": ["foo"]},
        {"packages": ["foo", "bar"]},
        {"packages": ["foo"], "extra_dirs": []},
        {"packages": [], "extra_dirs": []},
    ],
)
@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)
async def test_pkgconfig_resolve(
    pkg_config_service, foo_pc_file, bar_pc_file, set_pkg_config_path, spec_kwargs, request, pkgconfig_dir
):
    spec = PkgConfigSpec(**spec_kwargs)
    resolved = await pkg_config_service.resolve(spec)
    resolved.spec.extra_dirs = spec.extra_dirs
    if spec.extra_dirs:
        # Use Path.relative_to for stable, relative comparison
        resolved.spec.extra_dirs = [str(Path(d).relative_to(pkgconfig_dir)) for d in spec.extra_dirs]
    resolved.__test_name = request.node.name.strip()
    return resolved


@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)
async def test_pkgconfig_resolve_with_extra_dirs(pkg_config_service, foo_pc_file, pkgconfig_dir, request):
    spec = PkgConfigSpec(packages=["foo"], extra_dirs=[str(pkgconfig_dir)])
    resolved = await pkg_config_service.resolve(spec)
    resolved.spec.extra_dirs = [str(Path(d).relative_to(pkgconfig_dir)) for d in spec.extra_dirs]
    resolved.__test_name = request.node.name.strip()
    return resolved


@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)
async def test_pkgconfig_resolve_empty(pkg_config_service, request):
    spec = PkgConfigSpec(packages=[])
    resolved = await pkg_config_service.resolve(spec)
    resolved.__test_name = request.node.name.strip()
    return resolved


@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)
async def test_pkgconfig_resolve_missing(pkg_config_service, foo_pc_file, set_pkg_config_path, request):
    spec = PkgConfigSpec(packages=["foo", "missing"])
    with pytest.raises(process.ProcessError):
        await pkg_config_service.resolve(spec)
