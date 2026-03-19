"""Structure-from-Motion stage — wraps COLMAP and pyCuSFM."""

from __future__ import annotations

import shutil
from pathlib import Path

from bundle.core import logger
from bundle.core.data import Data
from bundle.core.process import ProcessStream

from ..contracts import SfmBackend, SfmInput, SfmOutput
from .base import Stage

log = logger.get_logger(__name__)


class SfmStage(Stage):
    """Thin wrapper around SfM backends (COLMAP / pyCuSFM).

    Constructs CLI arguments, runs the tool via subprocess, and validates
    the output contract.

    COLMAP pipeline:
        1. feature_extractor  — GPU-accelerated SIFT
        2. exhaustive_matcher  — pairwise feature matching
        3. mapper              — incremental sparse reconstruction
    """

    name: str = "sfm"
    backend: SfmBackend = SfmBackend.COLMAP
    use_gpu: bool = True
    matcher: str = "exhaustive"  # "exhaustive" | "sequential"

    async def run(self, input: Data) -> Data:
        assert isinstance(input, SfmInput)

        if self.backend == SfmBackend.COLMAP:
            return await self._run_colmap(input)

        raise NotImplementedError(f"Backend '{self.backend}' not yet implemented")

    async def check_deps(self) -> bool:
        if self.backend == SfmBackend.COLMAP:
            return shutil.which("colmap") is not None
        try:
            import pycusfm

            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # COLMAP implementation
    # ------------------------------------------------------------------

    async def _run_colmap(self, input: SfmInput) -> SfmOutput:
        """Run the COLMAP sparse reconstruction pipeline step-by-step."""
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

        # Build output contract
        # COLMAP mapper creates numbered subdirectories (0, 1, ...) for each model.
        # Pick the first one (largest/default reconstruction).
        model_dirs = sorted(p for p in sparse_dir.iterdir() if p.is_dir())
        if not model_dirs:
            raise RuntimeError(f"COLMAP mapper produced no models in {sparse_dir}")

        result = SfmOutput(
            sparse_dir=model_dirs[0],
            database_path=database_path,
            backend=SfmBackend.COLMAP,
        )

        if not result.validate_exists():
            raise RuntimeError(f"COLMAP output validation failed — check {sparse_dir}")

        log.info("COLMAP: sparse reconstruction complete — %s", result.sparse_dir)
        return result
