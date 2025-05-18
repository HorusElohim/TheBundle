import shutil
import sys
from pathlib import Path

import pytest
import pytest_asyncio  # Added import

from bundle.core import logger
from bundle.pybind.api import Pybind
from bundle.pybind.cmake import CMake

log = logger.get_logger(__name__)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="session")
async def built(tmp_path_factory):
    # 1) Copy entire example_module into a temp dir
    src = Path(__file__).parent / "example_module"
    log.testing(f"Copying example_module from {src} to temp dir")
    dest = tmp_path_factory.mktemp("example_module")
    shutil.copytree(src, dest, dirs_exist_ok=True)

    # Define build and install paths
    build_dir_name = "build"
    install_dir = dest / "install"

    # 2) Build & install C++ via CMake using the new CMake class
    await CMake.configure(source_dir=dest, build_dir_name=build_dir_name, install_prefix=install_dir)  # await async method
    await CMake.build(source_dir=dest, build_dir_name=build_dir_name, target="install")  # await async method
    # Note: api.set_pkg_config_path is now called by Pybind.set_pkg_config_path_from_install_prefix

    # Set PKG_CONFIG_PATH using the new Pybind method before building Python extensions
    await Pybind.set_pkgconfig_path(install_dir)

    # 3) Build Python extensions via bundle CLI
    await Pybind.build(dest)

    # 4) Prepend the bindings/python folder so imports work
    bindings_dir = dest / "bindings" / "python"
    sys.path.insert(0, str(bindings_dir))

    return dest


async def test_shape_module(built):
    import example_module.shape as sm

    c = sm.Circle(1.0)
    assert pytest.approx(c.area(), rel=1e-6) == 3.141592653589793

    s = sm.Square(2.0)
    assert s.area() == 4.0

    t = sm.Triangle(3.0, 4.0)
    assert t.area() == 0.5 * 3.0 * 4.0


async def test_geometry_module(built):
    import example_module.geometry as gm
    from example_module.shape import Circle, Square, Triangle

    shapes = [Circle(1.0), Square(2.0), Triangle(3.0, 4.0)]
    total = gm.wrap_shapes(shapes)
    expected = sum(s.area() for s in shapes)
    assert pytest.approx(total) == expected

    assert gm.maybe_make_square(False) is None
    sq = gm.maybe_make_square(True)
    assert isinstance(sq, Square)

    var = gm.get_shape_variant(False)
    assert isinstance(var, Square)

    comp = gm.make_composite()
    comp.add(Circle(1.0))
    comp.add(Square(1.0))
    assert pytest.approx(comp.area()) == (3.141592653589793 + 1.0)
