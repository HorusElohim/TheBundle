import os
import sys
import shutil
import sysconfig
import pytest
from pathlib import Path
import platform

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

    cmake_conf_cmd = ["cmake", "-S", ".", "-B", "build", "-DCMAKE_INSTALL_PREFIX=install"]

    # Append macOS-specific flag if needed
    if sys.platform == "darwin":
        import platform

        arch = platform.machine()
        cmake_conf_cmd.append(f"-DCMAKE_OSX_ARCHITECTURES={arch}")
        env = os.environ.copy()
        env["ARCHFLAGS"] = f"-arch {arch}"
        env["MACOSX_DEPLOYMENT_TARGET"] = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET") or "14.0"
    else:
        env = None

    # 2) Build & install C++ via CMake
    tracer.Sync.call_raise(proc.__call__, " ".join(cmake_conf_cmd), cwd=str(dest), env=env)
    tracer.Sync.call_raise(proc.__call__, "cmake --build build --target install", cwd=str(dest), env=env)

    # 3) Build Python extensions via bundle CLI
    api.set_pkg_config_path(dest / "install" / "lib" / "pkgconfig")
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
