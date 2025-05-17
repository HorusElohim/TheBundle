import os
import sys
import shutil
import pytest
from pathlib import Path

from bundle.core import logger
from bundle.core import tracer
from bundle.core.process import Process
from bundle.pybind import api

log = logger.get_logger(__name__)

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    # 1) Copy entire example_module into a temp dir
    src = Path(__file__).parent
    log.testing(f"Copying example_module from {src} to temp dir")
    dest = tmp_path_factory.mktemp("example_module")
    shutil.copytree(src, dest, dirs_exist_ok=True)

    proc = Process()

    # 2) Build & install C++ via CMake
    tracer.Sync.call_raise(
        proc.__call__,
        f"cmake -S . -B build -DCMAKE_INSTALL_PREFIX=install",
        cwd=str(dest),
    )
    tracer.Sync.call_raise(
        proc.__call__,
        "cmake --build build --target install",
        cwd=str(dest),
    )

    # 3) Build Python extensions via bundle CLI
    env = os.environ.copy()
    pkg_config_path = str(dest / "install" / "lib" / "pkgconfig")
    env["PKG_CONFIG_PATH"] = pkg_config_path

    # Also modify os.environ to ensure child processes inherit the variable
    orig_pkg_config = os.environ.get("PKG_CONFIG_PATH", "")
    os.environ["PKG_CONFIG_PATH"] = f"{orig_pkg_config}:{pkg_config_path}" if orig_pkg_config else pkg_config_path

    tracer.Sync.call_raise(api.build, dest)

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
