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
from bundle.testing import CppModulePath

EXAMPLE_MODULE_SRC_DIR = Path(__file__).parent / "example_module"

log = logger.get_logger(__name__)


@pytest.fixture(scope="session")
def get_tmp_cpp_module_path(tmp_path_factory, request) -> CppModulePath:
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

    example_module_path = CppModulePath(source=dest_proj_dir)

    return example_module_path


@pytest_asyncio.fixture(scope="session")
async def built_example_module(get_tmp_cpp_module_path: CppModulePath) -> CppModulePath:
    """Build and install the example module using CMakeService, return install_path."""
    log.testing("Building example module with CMakeService")
    cpp_module_path = get_tmp_cpp_module_path

    await CMakeService.configure(cpp_module_path.source, cpp_module_path.build, cpp_module_path.install)
    await CMakeService.build(cpp_module_path.source, cpp_module_path.build, target="install")

    return cpp_module_path


@pytest_asyncio.fixture(scope="session")
async def built_example_module_pybind(built_example_module: CppModulePath):
    """
    Build and install the example module using CMakeService, then build Python extensions via Pybind.
    Returns the actual build output path and pyproject.toml path.
    """
    cpp_module_path = built_example_module

    log.testing("Building Python bindings for example module")
    env = get_env_with_pkg_config_path([cpp_module_path.pkgconfig])
    os.environ.update(env)
    log.debug(f"Setting PKG_CONFIG_PATH to: {env['PKG_CONFIG_PATH']}")

    pyproject_path = cpp_module_path.source / "pyproject.toml"
    log.testing(f"Looking for pyproject.toml in {cpp_module_path.source}")
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found in {cpp_module_path.source}")

    await Pybind.build(cpp_module_path.source)

    # Without --inplace: find the real output directory
    if not cpp_module_path.build.exists():
        raise FileNotFoundError(f"Expected build/ directory not found in {cpp_module_path.source}")

    # Locate the first valid build output folder (e.g., build/lib.<platform>-cpython-<python-version>)
    for sub in cpp_module_path.build.iterdir():
        if sub.is_dir() and sub.name.startswith("lib."):
            sys.path.insert(0, str(sub))
            log.debug(f"Found and added compiled extension path to sys.path: {sub}")
            return sub, pyproject_path

    raise FileNotFoundError("Could not locate compiled extension output directory in build/")
