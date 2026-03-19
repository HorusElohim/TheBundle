"""Structure-from-Motion stage — wraps COLMAP and pyCuSFM."""

from __future__ import annotations

import shutil

from bundle.core import logger
from bundle.core.data import Data

from ..contracts import SfmBackend, SfmInput, SfmOutput
from .base import Stage

log = logger.get_logger(__name__)


class SfmStage(Stage):
    """Thin wrapper around SfM backends (COLMAP / pyCuSFM).

    Constructs CLI arguments, runs the tool via subprocess, and validates
    the output contract.  Implementation will be filled in once the pods
    are tested and the exact command-line interface is finalized.
    """

    name: str = "sfm"
    backend: SfmBackend = SfmBackend.COLMAP
    use_gpu: bool = True

    async def run(self, input: Data) -> Data:
        assert isinstance(input, SfmInput)
        raise NotImplementedError("SfM stage implementation pending — see pods/recon3d/sfm/")

    async def check_deps(self) -> bool:
        if self.backend == SfmBackend.COLMAP:
            return shutil.which("colmap") is not None
        # pyCuSFM is a Python package
        try:
            import pycusfm

            return True
        except ImportError:
            return False
