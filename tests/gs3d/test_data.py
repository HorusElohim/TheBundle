"""JSON round-trip tests for the gs3d metadata models."""

from __future__ import annotations

from pathlib import Path

import pytest

from bundle.gs3d.data import GaussianCloud, GaussianSequence

pytestmark = pytest.mark.asyncio


async def test_gaussian_cloud_defaults(tmp_path: Path) -> None:
    cloud = GaussianCloud(path=tmp_path / "missing.ply")
    assert cloud.num_gaussians == 0
    assert cloud.sh_degree == 3
    assert cloud.bbox_min == (0.0, 0.0, 0.0)
    assert cloud.bbox_max == (0.0, 0.0, 0.0)
    assert cloud.validate_exists() is False


async def test_gaussian_cloud_json_roundtrip(tmp_path: Path) -> None:
    original = GaussianCloud(
        path=tmp_path / "x.ply",
        num_gaussians=1234,
        sh_degree=2,
        bbox_min=(-1.0, -2.0, -3.0),
        bbox_max=(1.0, 2.0, 3.0),
    )
    payload = await original.as_json()
    revived = await GaussianCloud.from_json(payload)
    assert revived.num_gaussians == 1234
    assert revived.sh_degree == 2
    assert revived.bbox_min == (-1.0, -2.0, -3.0)
    assert revived.bbox_max == (1.0, 2.0, 3.0)
    assert revived.path == original.path


async def test_gaussian_sequence_validate_exists(tmp_path: Path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    f0 = frames_dir / "0000.ply"
    f1 = frames_dir / "0001.ply"
    f0.write_bytes(b"")
    f1.write_bytes(b"")

    seq = GaussianSequence(frames_dir=frames_dir, frame_count=2, fps=24.0, frame_paths=[f0, f1])
    assert seq.validate_exists() is True

    seq_missing = GaussianSequence(
        frames_dir=frames_dir,
        frame_count=2,
        frame_paths=[f0, frames_dir / "ghost.ply"],
    )
    assert seq_missing.validate_exists() is False
