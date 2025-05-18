import os
from pathlib import Path

import pytest

from bundle.pybind.services import PkgConfigService
from bundle.pybind.specs.pkgconfig import PkgConfigSpec

pytestmark = pytest.mark.asyncio


@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=10_000_000, performance_threshold=5_000_000)
async def test_cmake_and_pkgconfig_integration(built_example_module, request):
    """
    Integration test: build/install with CMakeService, then resolve with PkgConfigService.
    """
    # 1. Check install directory and .pc file
    install_prefix = built_example_module
    pc_dir = install_prefix / "lib" / "pkgconfig"
    pc_file = pc_dir / "example_module.pc"
    assert pc_file.is_file(), f".pc file not found at {pc_file}"

    # 2. Use PkgConfigService to resolve the installed package
    pkg_service = PkgConfigService()
    spec = PkgConfigSpec(packages=["example_module"], extra_dirs=[str(pc_dir)])
    resolved = await pkg_service.resolve(spec)
    # Clean extra_dirs for stable reference comparison
    resolved.spec.extra_dirs = [str(Path(d).relative_to(install_prefix)) for d in resolved.spec.extra_dirs]
    for pkg_resolved in resolved.resolved:
        pkg_resolved.include_dirs = [str(Path(d).relative_to(install_prefix)) for d in pkg_resolved.include_dirs]
        pkg_resolved.library_dirs = [str(Path(d).relative_to(install_prefix)) for d in pkg_resolved.library_dirs]
    resolved.__test_name = request.node.name.strip()
    return resolved
