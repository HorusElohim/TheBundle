import os
from pathlib import Path

import pytest

from bundle.core import logger, platform_info
from bundle.pybind.pybind import Pybind
from bundle.pybind.services.pkgconfig import get_env_with_pkg_config_path

log = logger.get_logger(__name__)

pytestmark = pytest.mark.asyncio

# Remove the built fixture and use built_example_module from conftest.py


async def test_project_pkg_path(built_example_module_pybind, built_example_module, request):
    pc_dir = built_example_module / "lib" / "pkgconfig"
    _bindings_dir, pyproject_path = built_example_module_pybind

    # Get modified environment and explicitly set it in os.environ
    env = get_env_with_pkg_config_path([pc_dir])
    os.environ["PKG_CONFIG_PATH"] = env["PKG_CONFIG_PATH"]
    log.debug(f"Set PKG_CONFIG_PATH={os.environ['PKG_CONFIG_PATH']}")

    # Debug explicitly by checking the existence of .pc files
    pc_files = list(pc_dir.glob("*.pc"))
    if not pc_files:
        raise FileNotFoundError(f"No pkg-config (.pc) files found in {pc_dir}")


@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)
async def test_project_resolved(built_example_module_pybind, built_example_module, request):
    pc_dir = built_example_module / "lib" / "pkgconfig"
    _bindings_dir, pyproject_path = built_example_module_pybind

    # Get modified environment and explicitly set it in os.environ
    env = get_env_with_pkg_config_path([pc_dir])
    os.environ["PKG_CONFIG_PATH"] = env["PKG_CONFIG_PATH"]
    log.debug(f"Set PKG_CONFIG_PATH={os.environ['PKG_CONFIG_PATH']}")

    project_resolved = await Pybind.info(pyproject_path.parent)

    # Make all relevant paths relative to the project root for stable references
    project_root = pyproject_path.parent

    # Fix module specs and resolved pkgconfig paths
    for module in project_resolved.modules:
        spec = module.spec
        # sources
        spec.sources = [str(Path(s).relative_to(project_root)) if Path(s).is_absolute() else s for s in spec.sources]
        # extra_compile_args and extra_link_args are usually flags, not paths, so skip
        # pkgconfig resolved paths
        pkg = module.pkgconfig
        for pkg_result in pkg.resolved:
            pkg_result.include_dirs = [
                str(Path(d).relative_to(project_root)) if Path(d).is_relative_to(str(project_root)) else d
                for d in pkg_result.include_dirs
            ]
            pkg_result.library_dirs = [
                str(Path(d).relative_to(project_root)) if Path(d).is_relative_to(str(project_root)) else d
                for d in pkg_result.library_dirs
            ]

    project_resolved.__test_name = request.node.name.strip()
    return project_resolved


async def test_shape_module(built_example_module_pybind):
    import example_module.shape as sm

    c = sm.Circle(1.0)
    assert pytest.approx(c.area(), rel=1e-6) == 3.141592653589793

    s = sm.Square(2.0)
    assert s.area() == 4.0

    t = sm.Triangle(3.0, 4.0)
    assert t.area() == 0.5 * 3.0 * 4.0


async def test_geometry_module(built_example_module_pybind):
    import example_module.geometry as gm
    from example_module.shape import Circle, Square, Triangle

    shapes = [Circle(1.0), Square(2.0), Triangle(3.0, 4.0)]
    total = gm.wrap_shapes(shapes)
    expected = sum(s.area() for s in shapes)
    assert pytest.approx(total) == expected

    assert gm.maybe_make_square(False) is None
    sq = gm.maybe_make_square(True)
    assert isinstance(sq, Square)

    comp = gm.make_composite()
    comp.add(Circle(1.0))
    comp.add(Square(1.0))
    assert pytest.approx(comp.area()) == (3.141592653589793 + 1.0)


@pytest.mark.xfail(reason="std::variant/pybind11 support may not be available on all platforms or Python/C++/OSX combinations")
async def test_geometry_module_variant(built_example_module_pybind):
    import example_module.geometry as gm
    from example_module.shape import Square

    gm.get_shape_variant(True)
    var = gm.get_shape_variant(False)
    assert isinstance(var, Square)
