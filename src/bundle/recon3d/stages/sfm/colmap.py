"""COLMAP Structure-from-Motion backend."""

from __future__ import annotations

import shutil
from pathlib import Path

from bundle.core import logger
from bundle.core.process import ProcessStream

from .base import SfmBackend, SfmInput, SfmOutput, SfmStage

log = logger.get_logger(__name__)


class ColmapSfm(SfmStage):
    """COLMAP sparse reconstruction pipeline.

    Runs three sequential steps via the ``colmap`` CLI:
        1. feature_extractor  — GPU-accelerated SIFT
        2. exhaustive_matcher  — pairwise feature matching
        3. mapper              — incremental sparse reconstruction
    """

    name: str = "sfm.colmap"
    backend: SfmBackend = SfmBackend.COLMAP

    async def _run(self, input: SfmInput) -> SfmOutput:
        output_dir = input.images_dir.parent / "sfm_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        database_path = output_dir / "database.db"
        sparse_dir = output_dir / "sparse"
        sparse_dir.mkdir(parents=True, exist_ok=True)

        gpu_flag = "1" if self.use_gpu else "0"
        proc = ProcessStream()

        # Step 1: Feature extraction
        log.info("COLMAP: extracting features from %s", input.images_dir)
        await proc(
            f"colmap feature_extractor"
            f" --database_path {database_path}"
            f" --image_path {input.images_dir}"
            f" --SiftExtraction.use_gpu {gpu_flag}"
        )

        # Step 2: Feature matching
        matcher_cmd = "exhaustive_matcher" if self.matcher == "exhaustive" else "sequential_matcher"
        log.info("COLMAP: running %s", matcher_cmd)
        await proc(f"colmap {matcher_cmd} --database_path {database_path} --SiftMatching.use_gpu {gpu_flag}")

        # Step 3: Sparse reconstruction (mapper)
        log.info("COLMAP: running mapper")
        await proc(f"colmap mapper --database_path {database_path} --image_path {input.images_dir} --output_path {sparse_dir}")

        # COLMAP mapper creates numbered subdirectories (0, 1, ...) for each model.
        # Pick the first one (largest/default reconstruction).
        model_dirs = sorted(p for p in sparse_dir.iterdir() if p.is_dir())
        if not model_dirs:
            raise RuntimeError(f"COLMAP mapper produced no models in {sparse_dir}")

        best_model = model_dirs[0]
        undistorted_images: Path | None = None

        # Step 4 (optional): Undistort images → converts SIMPLE_RADIAL etc. to PINHOLE
        if self.undistort:
            undistorted_dir = output_dir / "undistorted"
            log.info("COLMAP: undistorting images → %s", undistorted_dir)
            await proc(
                f"colmap image_undistorter"
                f" --image_path {input.images_dir}"
                f" --input_path {best_model}"
                f" --output_path {undistorted_dir}"
                f" --output_type COLMAP"
            )
            # image_undistorter writes sparse/ and images/ into undistorted_dir
            best_model = undistorted_dir / "sparse"
            undistorted_images = undistorted_dir / "images"

        result = SfmOutput(
            sparse_dir=best_model,
            database_path=database_path,
            images_dir=undistorted_images,
            backend=SfmBackend.COLMAP,
        )

        if not result.validate_exists():
            raise RuntimeError(f"COLMAP output validation failed — check {sparse_dir}")

        log.info("COLMAP: sparse reconstruction complete — %s", result.sparse_dir)
        return result

    async def check_deps(self) -> bool:
        return shutil.which("colmap") is not None
