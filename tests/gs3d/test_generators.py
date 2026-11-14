"""Tests for the procedural Gaussian generators."""

from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from bundle.gs3d.generators import (
    CubeGenerator,
    MeshToGaussiansGenerator,
    RandomCloudGenerator,
    SphereGenerator,
    TorusGenerator,
    available_shapes,
    create_generator,
)
from bundle.gs3d.generators.mesh import _normals_to_quaternions

# ---------------------------------------------------------------------------
# Registry (sync)
# ---------------------------------------------------------------------------


def test_available_shapes() -> None:
    assert set(available_shapes()) == {"sphere", "cube", "torus", "cloud", "mesh"}


def test_create_generator_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        create_generator("nonsense")


# ---------------------------------------------------------------------------
# Sphere
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sphere_surface_on_radius() -> None:
    cloud = await SphereGenerator(count=1024, radius=2.0, surface=True, seed=1).generate()
    assert len(cloud) == 1024
    np.testing.assert_allclose(np.linalg.norm(cloud.positions, axis=1), 2.0, atol=1e-3)


@pytest.mark.asyncio
async def test_sphere_volume_inside_radius() -> None:
    cloud = await SphereGenerator(count=512, radius=1.5, surface=False, seed=2).generate()
    assert (np.linalg.norm(cloud.positions, axis=1) <= 1.5 + 1e-5).all()


# ---------------------------------------------------------------------------
# Cube
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cube_interior_within_bounds() -> None:
    cloud = await CubeGenerator(count=400, size=1.0, surface=False, seed=3).generate()
    assert cloud.positions.min() >= -0.5 - 1e-5
    assert cloud.positions.max() <= 0.5 + 1e-5


@pytest.mark.asyncio
async def test_cube_surface_one_axis_pinned() -> None:
    cloud = await CubeGenerator(count=200, size=2.0, surface=True, seed=4).generate()
    on_face = np.isclose(np.abs(cloud.positions), 1.0, atol=1e-5)
    assert (on_face.sum(axis=1) == 1).all()


# ---------------------------------------------------------------------------
# Torus
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_torus_implicit_equation() -> None:
    R, r = 1.0, 0.3
    cloud = await TorusGenerator(count=400, major_radius=R, minor_radius=r, seed=5).generate()
    pos = cloud.positions
    rho = np.linalg.norm(pos[:, :2], axis=1)
    lhs = (rho - R) ** 2 + pos[:, 2] ** 2
    np.testing.assert_allclose(lhs, r * r, atol=1e-4)


# ---------------------------------------------------------------------------
# Random cloud
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_random_cloud_within_bounds() -> None:
    bounds_min = (-2.0, 0.0, 1.0)
    bounds_max = (2.0, 4.0, 3.0)
    cloud = await RandomCloudGenerator(count=300, bounds_min=bounds_min, bounds_max=bounds_max, seed=6).generate()
    pos = cloud.positions
    for i, (lo, hi) in enumerate(zip(bounds_min, bounds_max, strict=True)):
        assert (pos[:, i] >= lo).all() and (pos[:, i] <= hi).all()


# ---------------------------------------------------------------------------
# Shared properties
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_determinism() -> None:
    a = await SphereGenerator(count=64, seed=42).generate()
    b = await SphereGenerator(count=64, seed=42).generate()
    np.testing.assert_array_equal(a.data["x"], b.data["x"])


@pytest.mark.asyncio
async def test_factory_dispatches_and_generates() -> None:
    gen = create_generator("cube", count=10, size=3.0, seed=0)
    assert isinstance(gen, CubeGenerator)
    cloud = await gen.generate()
    assert len(cloud) == 10
    assert (np.abs(cloud.positions) <= 1.5 + 1e-5).all()


# ---------------------------------------------------------------------------
# Mesh helper
# ---------------------------------------------------------------------------


def test_normals_to_quaternions_canonical() -> None:
    n = np.array([[0, 0, 1], [0, 0, -1], [1, 0, 0]], dtype=np.float32)
    q = _normals_to_quaternions(n)
    np.testing.assert_allclose(q[0], [1, 0, 0, 0], atol=1e-5)
    np.testing.assert_allclose(q[1], [0, 1, 0, 0], atol=1e-5)
    np.testing.assert_allclose(q[2], [math.cos(math.pi / 4), 0, math.sin(math.pi / 4), 0], atol=1e-5)
    np.testing.assert_allclose(np.linalg.norm(q, axis=1), 1.0, atol=1e-5)


@pytest.mark.asyncio
async def test_mesh_generator_deferred_import(tmp_path) -> None:
    gen = MeshToGaussiansGenerator(source=tmp_path / "nope.obj", count=10)
    try:
        import trimesh

        expected = FileNotFoundError
    except ImportError:
        expected = ImportError
    with pytest.raises(expected):
        await gen.generate()
