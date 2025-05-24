import os
from pathlib import Path

import pytest

from bundle.pybind.services import CMakeService

pytestmark = pytest.mark.asyncio

# Helper to get the example_module path relative to this test file
EXAMPLE_MODULE_SRC_DIR = Path(__file__).parent.parent / "example_module"


async def test_cmake_configure(get_tmp_example_module: Path):
    """Tests the CMakeService.configure method."""
    source_dir = get_tmp_example_module
    build_dir_name = "build_configure_test"
    install_prefix = source_dir / "install_configure_test"

    await CMakeService.configure(source_dir, build_dir_name, install_prefix=install_prefix)

    build_path = source_dir / build_dir_name
    assert build_path.is_dir(), "Build directory was not created"
    assert (build_path / "CMakeCache.txt").is_file(), "CMakeCache.txt not found in build directory"

    # Verify CMAKE_INSTALL_PREFIX in CMakeCache.txt (compare only the basename for stability)
    cache_content = (build_path / "CMakeCache.txt").read_text()
    assert f"CMAKE_INSTALL_PREFIX:PATH={install_prefix.resolve().as_posix()}" in cache_content


async def test_cmake_build_and_install(get_tmp_example_module: Path):
    """Tests the CMakeService.build method, including the install target."""
    source_dir = get_tmp_example_module
    build_dir_name = "build_and_install_test"
    install_prefix = source_dir / "install_dir_for_build_test"

    # 1. Configure the project
    await CMakeService.configure(source_dir, build_dir_name, install_prefix=install_prefix)

    # 2. Build the default target
    await CMakeService.build(source_dir, build_dir_name)
    # Check for an expected artifact (specific to example_module)
    # This assumes example_module produces libexample_module.a or similar in the build tree.
    # A more generic check is that the command doesn't fail.
    # For example_module, specific library files are in build_dir_name/libexample_module.*
    # We can check if the build directory contains some files.
    assert any((source_dir / build_dir_name).iterdir()), "Build directory is empty after default build"

    # 3. Build the install target
    original_pkg_config_path_env = os.environ.get("PKG_CONFIG_PATH")

    try:
        await CMakeService.build(source_dir, build_dir_name, target="install")

        assert install_prefix.is_dir(), "Install directory was not created"

        # Check for an installed .pc file (compare only the filename for stability)
        pc_file = install_prefix / "lib" / "pkgconfig" / "example_module.pc"
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
