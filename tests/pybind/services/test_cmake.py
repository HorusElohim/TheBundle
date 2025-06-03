import os
from pathlib import Path

import pytest

from bundle.pybind.services import CMakeService
from bundle.testing import CppModulePath

pytestmark = pytest.mark.asyncio

# Helper to get the example_module path relative to this test file
EXAMPLE_MODULE_SRC_DIR = Path(__file__).parent.parent / "example_module"


async def test_cmake_configure(get_tmp_cpp_module_path: CppModulePath):
    """Tests the CMakeService.configure method."""

    cpp_module_path = get_tmp_cpp_module_path

    await CMakeService.configure(cpp_module_path.source, cpp_module_path.build, install_path=cpp_module_path.install)
    assert cpp_module_path.build.is_dir(), "Build directory was not created"
    assert (cpp_module_path.build / "CMakeCache.txt").is_file(), "CMakeCache.txt not found in build directory"

    # Verify CMAKE_INSTALL_PREFIX in CMakeCache.txt (compare only the basename for stability)
    cache_content = (cpp_module_path.build / "CMakeCache.txt").read_text()
    assert f"CMAKE_INSTALL_PREFIX:PATH={cpp_module_path.install.as_posix()}" in cache_content


async def test_cmake_build_and_install(get_tmp_cpp_module_path: CppModulePath):
    """Tests the CMakeService.build method, including the install target."""
    cpp_module_path = get_tmp_cpp_module_path

    # 1. Configure the project
    await CMakeService.configure(cpp_module_path.source, cpp_module_path.build, install_path=cpp_module_path.install)

    # 2. Build the default target
    await CMakeService.build(cpp_module_path.source, cpp_module_path.build, target="install")
    # Check for an expected artifact (specific to example_module)
    # This assumes example_module produces libexample_module.a or similar in the build tree.
    # A more generic check is that the command doesn't fail.
    # For example_module, specific library files are in cpp_module_path.build/libexample_module.*
    # We can check if the build directory contains some files.
    assert any((cpp_module_path.source / cpp_module_path.build).iterdir()), "Build directory is empty after default build"

    # 3. Build the install target
    original_pkg_config_path_env = os.environ.get("PKG_CONFIG_PATH")

    try:
        await CMakeService.build(cpp_module_path.source, cpp_module_path.build, target="install")
        assert cpp_module_path.install.is_dir(), "Install directory was not created"
        # Check for an installed .pc file (compare only the filename for stability)
        pc_file = cpp_module_path.install / "lib" / "pkgconfig" / "example_module.pc"
        assert pc_file.is_file(), f".pc file not found at {pc_file}"

    except Exception as e:
        raise e

    finally:
        # Restore original PKG_CONFIG_PATH state
        if original_pkg_config_path_env is None:
            if "PKG_CONFIG_PATH" in os.environ:
                del os.environ["PKG_CONFIG_PATH"]
        else:
            os.environ["PKG_CONFIG_PATH"] = original_pkg_config_path_env
