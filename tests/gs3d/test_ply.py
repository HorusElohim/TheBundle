"""Round-trip tests for the 3DGS PLY reader/writer."""

from __future__ import annotations

from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from bundle.gs3d.ply import (
    GaussianCloudArrays,
    property_names,
    read_ply,
    read_ply_header,
    sh_rest_count,
    write_ply,
)


def test_sh_rest_count_table() -> None:
    # SH degree N has (N+1)^2 coefficients per channel; subtract DC and times 3 RGB.
    assert sh_rest_count(0) == 0
    assert sh_rest_count(1) == 9  # 3 * (4 - 1)
    assert sh_rest_count(2) == 24  # 3 * (9 - 1)
    assert sh_rest_count(3) == 45  # 3 * (16 - 1)


def test_property_names_layout() -> None:
    names = property_names(3)
    # 3 xyz + 3 nxnynz + 3 f_dc + 45 f_rest + 1 opacity + 3 scale + 4 rot = 62
    assert len(names) == 62
    assert names[:6] == ["x", "y", "z", "nx", "ny", "nz"]
    assert names[-4:] == ["rot_0", "rot_1", "rot_2", "rot_3"]
    assert "f_rest_0" in names and "f_rest_44" in names


@pytest.mark.asyncio
@pytest.mark.parametrize("sh_degree", [0, 1, 3])
async def test_write_then_read_roundtrip(tmp_path: Path, sh_degree: int) -> None:
    cloud = GaussianCloudArrays.empty(count=128, sh_degree=sh_degree)
    rng = np.random.default_rng(0)
    cloud.data["x"] = rng.standard_normal(128).astype(np.float32)
    cloud.data["y"] = rng.standard_normal(128).astype(np.float32)
    cloud.data["z"] = rng.standard_normal(128).astype(np.float32)
    cloud.data["opacity"] = 1.5
    cloud.data["scale_0"] = -3.0
    cloud.data["scale_1"] = -3.0
    cloud.data["scale_2"] = -3.0
    cloud.data["rot_0"] = 1.0  # identity quaternion
    cloud.data["f_dc_0"] = 0.123

    path = tmp_path / f"sh{sh_degree}.ply"
    meta = await write_ply(path, cloud)
    assert meta.num_gaussians == 128
    assert meta.sh_degree == sh_degree
    assert path.exists()

    # Header-only read should report the same metadata without touching the payload.
    head = await read_ply_header(path)
    assert head.num_gaussians == 128
    assert head.sh_degree == sh_degree

    # Full read should yield byte-for-byte identical floats.
    rt = await read_ply(path)
    assert len(rt) == 128
    assert rt.sh_degree == sh_degree
    np.testing.assert_array_equal(rt.data["x"], cloud.data["x"])
    np.testing.assert_array_equal(rt.data["f_dc_0"], cloud.data["f_dc_0"])


def test_bbox_from_positions() -> None:
    cloud = GaussianCloudArrays.empty(count=4, sh_degree=0)
    cloud.data["x"] = np.array([-1.0, 1.0, 0.5, -0.5], dtype=np.float32)
    cloud.data["y"] = np.array([-2.0, 2.0, 0.0, 0.0], dtype=np.float32)
    cloud.data["z"] = np.array([-3.0, 3.0, 0.0, 0.0], dtype=np.float32)
    bmin, bmax = cloud.bbox()
    assert bmin == (-1.0, -2.0, -3.0)
    assert bmax == (1.0, 2.0, 3.0)


@pytest.mark.asyncio
async def test_read_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        await read_ply(tmp_path / "nope.ply")
    with pytest.raises(FileNotFoundError):
        await read_ply_header(tmp_path / "nope.ply")
