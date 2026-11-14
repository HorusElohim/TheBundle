"""Abstract base for synthetic Gaussian generators.

A generator is an :class:`Entity` with a single async ``generate`` method that
produces a :class:`GaussianCloudArrays`.  Generator parameters live directly
on the class as Pydantic fields — no separate ``Config`` object — matching
the :class:`bundle.recon3d.stages.base.Stage` pattern where stage parameters
are just fields on the stage.
"""

from __future__ import annotations

from abc import abstractmethod

from bundle.core import logger
from bundle.core.entity import Entity

from ..ply import GaussianCloudArrays

log = logger.get_logger(__name__)


class Generator(Entity):
    """Base class for procedural Gaussian generators.

    Subclasses add shape-specific fields and implement :meth:`generate`.

    Attributes:
        count: Number of Gaussians to emit.
        sh_degree: Spherical harmonics degree (0..3).
        seed: Random seed; ``None`` for non-deterministic output.
        opacity: Logit-space opacity assigned to each generated Gaussian
            (logit ~2.0 ≈ alpha 0.88).
        base_scale: Initial isotropic log-space scale (``exp(-3) ≈ 0.05``).
        color: Linear-space RGB colour written into the SH DC term.
    """

    name: str = "generator"
    count: int = 10_000
    sh_degree: int = 3
    seed: int | None = None
    opacity: float = 2.0
    base_scale: float = -3.0
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)

    @abstractmethod
    async def generate(self) -> GaussianCloudArrays:
        """Produce a :class:`GaussianCloudArrays` from this generator's parameters."""
        ...
