"""Dataset management for the Recon3D pipeline.

Handles downloading, extracting, and locating benchmark datasets used
for testing and evaluation.  Datasets are stored in a shared data root
accessible to all recon3d pods.
"""

from __future__ import annotations

import zipfile
from enum import Enum
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data
from bundle.core.downloader import DownloaderTQDM

log = logger.get_logger(__name__)

DEFAULT_DATA_ROOT = Path("/workspace/data")  # inside containers; override with --data-root or RECON3D_DATA_ROOT


class DatasetId(str, Enum):
    """Known benchmark datasets."""

    MIP_NERF_360 = "360_v2"


# Registry: dataset_id -> (url, archive_name, known_scenes)
# known_scenes is used to detect whether extraction already happened
# (the 360_v2.zip extracts scenes flat, with no top-level directory).
DATASET_REGISTRY: dict[DatasetId, tuple[str, str, list[str]]] = {
    DatasetId.MIP_NERF_360: (
        "http://storage.googleapis.com/gresearch/refraw360/360_v2.zip",
        "360_v2.zip",
        ["bicycle", "bonsai", "counter", "garden", "kitchen", "room", "stump"],
    ),
}


class DatasetInfo(Data):
    """Metadata about a fetched dataset."""

    dataset_id: DatasetId
    root: Path
    scenes: list[str]


async def fetch(
    dataset_id: DatasetId,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> DatasetInfo:
    """Download and extract a dataset if not already present.

    Args:
        dataset_id: Which dataset to fetch.
        data_root: Root directory for all datasets.

    Returns:
        DatasetInfo with the extracted root and available scenes.
    """
    url, archive_name, known_scenes = DATASET_REGISTRY[dataset_id]
    data_root = data_root.resolve()
    data_root.mkdir(parents=True, exist_ok=True)

    archive_path = data_root / archive_name

    # Check if already extracted (look for any known scene directory)
    already_extracted = any((data_root / s).is_dir() for s in known_scenes)

    if not already_extracted:
        # Download
        if not archive_path.exists():
            log.info("Downloading %s -> %s", url, archive_path)
            ok = await DownloaderTQDM(url=url, destination=archive_path).download()
            if not ok:
                raise RuntimeError(f"Failed to download {url}")
        else:
            log.info("Archive already cached: %s", archive_path)

        # Extract (360_v2.zip extracts scenes flat into data_root)
        log.info("Extracting %s -> %s", archive_path, data_root)
        with zipfile.ZipFile(archive_path, "r") as fh:
            fh.extractall(data_root)

        log.info("Extraction complete: %s", data_root)
    else:
        log.info("Dataset already present: %s", data_root)

    # Discover available scenes (subdirectories with images)
    scenes = sorted(p.name for p in data_root.iterdir() if p.is_dir() and _is_scene(p))

    return DatasetInfo(dataset_id=dataset_id, root=data_root, scenes=scenes)


def locate_scene(dataset_root: Path, scene: str) -> Path:
    """Find the images directory for a scene within an extracted dataset.

    Prefers lower resolution variants to keep tests fast:
    images_4 > images_2 > images (following the ppisp convention).

    Args:
        dataset_root: Root of the extracted dataset (e.g. /workspace/data/360_v2).
        scene: Scene name (e.g. "bicycle").

    Returns:
        Path to the images directory.
    """
    scene_dir = dataset_root / scene
    if not scene_dir.is_dir():
        available = sorted(p.name for p in dataset_root.iterdir() if p.is_dir())
        raise FileNotFoundError(f"Scene '{scene}' not found in {dataset_root}. Available: {available}")

    # Prefer full resolution for SfM (features need detail), fallback to downsampled
    for name in ("images", "images_2", "images_4"):
        p = scene_dir / name
        if p.is_dir() and _is_scene(p):
            return p

    raise FileNotFoundError(f"No images found in scene '{scene}' at {scene_dir}")


def _is_scene(directory: Path) -> bool:
    """Check if a directory looks like a scene (contains an images/ subdirectory with image files)."""
    for name in ("images", "images_2", "images_4", "images_8"):
        img_dir = directory / name
        if img_dir.is_dir() and any(f.suffix.lower() in {".jpg", ".jpeg", ".png"} for f in img_dir.iterdir() if f.is_file()):
            return True
    return False
