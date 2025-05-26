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


@pytest.fixture(scope="session")
def get_tmp_example_module(tmp_path_factory, request):
    """Copies the example_module to a temporary directory for CMake testing."""
    log.testing("Copying example module to temporary directory for testing")
    if not EXAMPLE_MODULE_SRC_DIR.exists():
        raise FileNotFoundError(f"Example module source directory does not exist: {EXAMPLE_MODULE_SRC_DIR}")

    dest_proj_dir = tmp_path_factory.mktemp("tests_example_module")
    shutil.copytree(EXAMPLE_MODULE_SRC_DIR, dest_proj_dir, dirs_exist_ok=True)
    log.testing(f"Example module copied to: {dest_proj_dir}")

    # Register for cleanup logging
    session = request.session
    if not hasattr(session, "collected_temp_dirs"):
        session.collected_temp_dirs = []
    session.collected_temp_dirs.append(dest_proj_dir)
    return dest_proj_dir


@pytest_asyncio.fixture
async def built_example_module(get_tmp_example_module: Path):
    """Build and install the example module using CMakeService, return install_path."""
    log.testing("Building example module with CMakeService")
    source_path = get_tmp_example_module
    build_path = get_tmp_example_module / "integration_build"
    install_path = source_path / "install"

    await CMakeService.configure(source_path, build_path, install_path)
    await CMakeService.build(source_path, build_path, target="install")

    return install_path


@pytest_asyncio.fixture
async def built_example_module_pybind(built_example_module: Path):
    """
    Build and install the example module using CMakeService, then build Python extensions via Pybind.
    Returns the actual build output path and pyproject.toml path.
    """
    log.testing("Building Python bindings for example module")
    dest = built_example_module
    pc_path = dest / "lib" / "pkgconfig"
    env = get_env_with_pkg_config_path([pc_path])
    os.environ.update(env)
    log.debug(f"Setting PKG_CONFIG_PATH to: {env['PKG_CONFIG_PATH']}")

    source_path = dest.parent  # e.g. tests_example_module/install -> tests_example_module
    pyproject_path = source_path / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found in {source_path}")

    await Pybind.build(source_path)

    # Without --inplace: find the real output directory
    build_dir = source_path / "build"
    if not build_dir.exists():
        raise FileNotFoundError(f"Expected build/ directory not found in {source_path}")

    # Locate the first valid build output folder (e.g., build/lib.<platform>-cpython-<python-version>)
    for sub in build_dir.iterdir():
        if sub.is_dir() and sub.name.startswith("lib."):
            sys.path.insert(0, str(sub))
            log.debug(f"Found and added compiled extension path to sys.path: {sub}")
            return sub, pyproject_path

    raise FileNotFoundError("Could not locate compiled extension output directory in build/")
