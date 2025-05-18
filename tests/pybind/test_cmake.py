import os
import pytest
from pathlib import Path
import shutil
import sysconfig

from bundle.pybind.cmake import CMake
from bundle.pybind import api # For checking side effects on PKG_CONFIG_PATH

# Helper to get the example_module path relative to this test file
EXAMPLE_MODULE_SRC_DIR = Path(__file__).parent / "example_module"


@pytest.fixture(scope="module")
def cmake_test_project(tmp_path_factory):
    """Copies the example_module to a temporary directory for CMake testing."""
    if not EXAMPLE_MODULE_SRC_DIR.exists():
        pytest.skip(f"example_module directory not found at {EXAMPLE_MODULE_SRC_DIR}")

    dest_proj_dir = tmp_path_factory.mktemp("cmake_test_project_root")
    shutil.copytree(EXAMPLE_MODULE_SRC_DIR, dest_proj_dir, dirs_exist_ok=True)
    return dest_proj_dir


def test_cmake_configure(cmake_test_project: Path):
    """Tests the CMake.configure method."""
    source_dir = cmake_test_project
    build_dir_name = "build_configure_test"
    install_prefix = source_dir / "install_configure_test"

    CMake.configure(source_dir, build_dir_name, install_prefix=install_prefix)

    build_path = source_dir / build_dir_name
    assert build_path.is_dir(), "Build directory was not created"
    assert (build_path / "CMakeCache.txt").is_file(), "CMakeCache.txt not found in build directory"

    # Verify CMAKE_INSTALL_PREFIX in CMakeCache.txt (optional, more robust check)
    cache_content = (build_path / "CMakeCache.txt").read_text()
    assert f"CMAKE_INSTALL_PREFIX:PATH={install_prefix.resolve()}" in cache_content


def test_cmake_build_and_install(cmake_test_project: Path):
    """Tests the CMake.build method, including the install target."""
    source_dir = cmake_test_project
    build_dir_name = "build_and_install_test"
    install_prefix = source_dir / "install_dir_for_build_test"

    # 1. Configure the project
    CMake.configure(source_dir, build_dir_name, install_prefix=install_prefix)

    # 2. Build the default target
    CMake.build(source_dir, build_dir_name)
    # Check for an expected artifact (specific to example_module)
    # This assumes example_module produces libexample_module.a or similar in the build tree.
    # A more generic check is that the command doesn't fail.
    # For example_module, specific library files are in build_dir_name/libexample_module.*
    # We can check if the build directory contains some files.
    assert any((source_dir / build_dir_name).iterdir()), "Build directory is empty after default build"

    # 3. Build the install target
    original_pkg_config_path_env = os.environ.get("PKG_CONFIG_PATH")
    
    try:
        CMake.build(
            source_dir,
            build_dir_name,
            target="install"
        )

        assert install_prefix.is_dir(), "Install directory was not created"
        
        # Check for an installed file (specific to example_module)
        pc_file = install_prefix / "lib" / "pkgconfig" / "example_module.pc"
        assert pc_file.is_file(), f".pc file not found at {pc_file}"

    finally:
        # Restore original PKG_CONFIG_PATH state
        if original_pkg_config_path_env is None:
            if "PKG_CONFIG_PATH" in os.environ:
                del os.environ["PKG_CONFIG_PATH"]
        else:
            os.environ["PKG_CONFIG_PATH"] = original_pkg_config_path_env
