"""Gaussian splatting stage — wraps 3DGRUT."""

from __future__ import annotations

from bundle.core import logger
from bundle.core.data import Data

from ..contracts import GaussiansInput, GaussiansOutput
from .base import Stage

log = logger.get_logger(__name__)


class GaussiansStage(Stage):
    """Thin wrapper around 3DGRUT training and export.

    Constructs Hydra config overrides, runs train.py via subprocess, and
    validates the output contract.  Implementation will be filled in once
    the 3DGRUT pod is tested end-to-end.
    """

    name: str = "gaussians"
    renderer: str = "3dgut"  # "3dgut" | "3dgrt"
    export_usdz: bool = True

    async def run(self, input: Data) -> Data:
        assert isinstance(input, GaussiansInput)
        raise NotImplementedError("Gaussians stage implementation pending — see pods/recon3d/gaussians/")

    async def check_deps(self) -> bool:
        try:
            import threedgrut

            return True
        except ImportError:
            return False
