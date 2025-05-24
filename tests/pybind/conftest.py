import os
import shutil
import sys
from pathlib import Path

import pytest
import pytest_asyncio

from bundle.core import logger
from bundle.pybind.pybind import Pybind
from bundle.pybind.services import CMakeService
from bundle.pybind.services.pkgconfig import get_env_with_pkg_config_path

EXAMPLE_MODULE_SRC_DIR = Path(__file__).parent / "example_module"

log = logger.get_logger(__name__)


@pytest.fixture(scope="module")
def get_tmp_example_module(tmp_path_factory):
    """Copies the example_module to a temporary directory for CMake testing."""
    log.testing("Copying example module to temporary directory for testing")
    if not EXAMPLE_MODULE_SRC_DIR.exists():
        raise FileNotFoundError(f"Example module source directory does not exist: {EXAMPLE_MODULE_SRC_DIR}")

    dest_proj_dir = tmp_path_factory.mktemp("tests_example_module")
    shutil.copytree(EXAMPLE_MODULE_SRC_DIR, dest_proj_dir, dirs_exist_ok=True)
    log.testing(f"Example module copied to: {dest_proj_dir}")
    return dest_proj_dir


@pytest_asyncio.fixture
async def built_example_module(get_tmp_example_module: Path):
    """Build and install the example module using CMakeService, return install_prefix."""
    log.testing("Building example module with CMakeService")
    source_dir = get_tmp_example_module
    build_dir_name = "integration_build"
    install_prefix = source_dir / "install"

    await CMakeService.configure(source_dir, build_dir_name, install_prefix=install_prefix)
    await CMakeService.build(source_dir, build_dir_name, target="install")

    return install_prefix


@pytest_asyncio.fixture
async def built_example_module_pybind(built_example_module: Path):
    """
    Build and install the example module using CMakeService, then build Python extensions via Pybind.
    Returns the install_prefix (not the bindings dir).
    """
    log.testing("Building Python bindings for example module")
    dest = built_example_module
    pc_path = dest / "lib" / "pkgconfig"
    env = get_env_with_pkg_config_path([pc_path])
    log.debug(f"Setting PKG_CONFIG_PATH to: {env['PKG_CONFIG_PATH']}")
    os.environ.update(env)

    # The Python bindings are built in the source tree, not in the install dir.
    source_dir = dest.parent  # tests_example_module/install -> tests_example_module
    pyproject_path = source_dir / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found in {source_dir}")
    await Pybind.build(source_dir)
    bindings_dir = source_dir / "bindings" / "python"
    bindings_dir = bindings_dir.resolve()
    if not bindings_dir.exists():
        raise FileNotFoundError(f"Bindings directory not found: {bindings_dir}")
    log.debug(f"Adding bindings_dir in PATH: {bindings_dir}")
    sys.path.insert(0, str(bindings_dir))
    return bindings_dir, pyproject_path
