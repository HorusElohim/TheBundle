"""Procedural primitive generators: sphere, cube, torus, random cloud.

Each generator allocates a :class:`GaussianCloudArrays` of the requested
size and fills the position, scale, rotation, opacity, and SH DC channels.
SH degrees > 0 leave the higher-order ``f_rest_*`` coefficients zero — view-
dependent appearance is opt-in for synthetic content.

Colours are written into the SH DC term using the same constant the
inria-graphdeco reference uses (``C0 = 0.28209479177387814``), so a
DC value of ``(c - 0.5) / C0`` reproduces a constant linear colour ``c``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from bundle.core import logger

from ..ply import GaussianCloudArrays
from .base import Generator

if TYPE_CHECKING:
    import numpy as np

log = logger.get_logger(__name__)

# Spherical harmonic DC normalisation constant (matches gaussian-splatting/utils/sh_utils.py).
SH_C0 = 0.28209479177387814


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rng(seed: int | None):
    """Create a numpy random Generator. Lazily imports numpy."""
    import numpy as np

    return np.random.default_rng(seed)


def _fill_common(
    arr: np.ndarray,
    *,
    positions: np.ndarray,
    color: tuple[float, float, float],
    opacity: float,
    base_scale: float,
) -> None:
    """Populate the shared fields of a 3DGS structured array.

    Writes positions, identity quaternion (wxyz = 1,0,0,0), isotropic scale,
    opacity, and SH DC color. Higher-order SH coefficients are left at zero.
    """
    arr["x"] = positions[:, 0]
    arr["y"] = positions[:, 1]
    arr["z"] = positions[:, 2]
    arr["scale_0"] = base_scale
    arr["scale_1"] = base_scale
    arr["scale_2"] = base_scale
    arr["rot_0"] = 1.0  # w
    arr["rot_1"] = 0.0
    arr["rot_2"] = 0.0
    arr["rot_3"] = 0.0
    arr["opacity"] = opacity
    arr["f_dc_0"] = (color[0] - 0.5) / SH_C0
    arr["f_dc_1"] = (color[1] - 0.5) / SH_C0
    arr["f_dc_2"] = (color[2] - 0.5) / SH_C0


# ---------------------------------------------------------------------------
# Sphere
# ---------------------------------------------------------------------------


class SphereGenerator(Generator):
    """Gaussians distributed uniformly on (or in) a sphere.

    Attributes:
        radius: Sphere radius.
        center: Sphere centre in world space.
        surface: When ``True`` samples lie on the surface; otherwise inside.
    """

    name: str = "sphere"
    radius: float = 1.0
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    surface: bool = True

    async def generate(self) -> GaussianCloudArrays:
        import numpy as np

        rng = _rng(self.seed)
        n = self.count

        # Sample uniform points on the unit sphere via normalised gaussians.
        v = rng.standard_normal((n, 3)).astype(np.float32)
        v /= np.linalg.norm(v, axis=1, keepdims=True) + 1e-8

        if self.surface:
            r = np.full((n, 1), self.radius, dtype=np.float32)
        else:
            # Volume-uniform: r ~ U^(1/3)
            r = (rng.random((n, 1)).astype(np.float32) ** (1.0 / 3.0)) * self.radius

        positions = v * r + np.asarray(self.center, dtype=np.float32)

        cloud = GaussianCloudArrays.empty(n, sh_degree=self.sh_degree)
        # Scale matches the local point spacing on the surface: ~ radius / sqrt(N).
        local_scale = math.log(max(self.radius / max(math.sqrt(n), 1.0), 1e-6))
        _fill_common(
            cloud.data,
            positions=positions,
            color=self.color,
            opacity=self.opacity,
            base_scale=local_scale,
        )
        log.info("SphereGenerator: %d gaussians, radius=%.3f, surface=%s", n, self.radius, self.surface)
        return cloud


# ---------------------------------------------------------------------------
# Cube
# ---------------------------------------------------------------------------


class CubeGenerator(Generator):
    """Gaussians inside (or on the surface of) an axis-aligned cube.

    Attributes:
        size: Edge length.
        center: Cube centre.
        surface: When ``True`` samples lie on the six faces; otherwise inside.
    """

    name: str = "cube"
    size: float = 1.0
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    surface: bool = False

    async def generate(self) -> GaussianCloudArrays:
        import numpy as np

        rng = _rng(self.seed)
        n = self.count
        half = self.size / 2.0
        center = np.asarray(self.center, dtype=np.float32)

        if not self.surface:
            positions = rng.uniform(-half, half, size=(n, 3)).astype(np.float32) + center
        else:
            # Pick a random face per sample, then uniform on that face.
            faces = rng.integers(0, 6, size=n)
            uv = rng.uniform(-half, half, size=(n, 2)).astype(np.float32)
            positions = np.zeros((n, 3), dtype=np.float32)
            for i in range(n):
                f = faces[i]
                axis = f // 2
                sign = 1.0 if (f % 2 == 0) else -1.0
                others = [a for a in range(3) if a != axis]
                positions[i, axis] = sign * half
                positions[i, others[0]] = uv[i, 0]
                positions[i, others[1]] = uv[i, 1]
            positions += center

        cloud = GaussianCloudArrays.empty(n, sh_degree=self.sh_degree)
        local_scale = math.log(max(self.size / max(n ** (1.0 / 3.0), 1.0), 1e-6))
        _fill_common(
            cloud.data,
            positions=positions,
            color=self.color,
            opacity=self.opacity,
            base_scale=local_scale,
        )
        log.info("CubeGenerator: %d gaussians, size=%.3f, surface=%s", n, self.size, self.surface)
        return cloud


# ---------------------------------------------------------------------------
# Torus
# ---------------------------------------------------------------------------


class TorusGenerator(Generator):
    """Gaussians on a torus surface in the XY plane.

    Attributes:
        major_radius: Distance from torus centre to tube centre (R).
        minor_radius: Tube radius (r).
        center: Torus centre.
    """

    name: str = "torus"
    major_radius: float = 1.0
    minor_radius: float = 0.3
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)

    async def generate(self) -> GaussianCloudArrays:
        import numpy as np

        rng = _rng(self.seed)
        n = self.count
        u = rng.uniform(0.0, 2.0 * math.pi, size=n).astype(np.float32)
        v = rng.uniform(0.0, 2.0 * math.pi, size=n).astype(np.float32)
        R, r = self.major_radius, self.minor_radius

        x = (R + r * np.cos(v)) * np.cos(u)
        y = (R + r * np.cos(v)) * np.sin(u)
        z = r * np.sin(v)
        positions = np.stack([x, y, z], axis=-1).astype(np.float32) + np.asarray(self.center, dtype=np.float32)

        cloud = GaussianCloudArrays.empty(n, sh_degree=self.sh_degree)
        local_scale = math.log(max((2 * math.pi * R) / max(math.sqrt(n), 1.0), 1e-6))
        _fill_common(
            cloud.data,
            positions=positions,
            color=self.color,
            opacity=self.opacity,
            base_scale=local_scale,
        )
        log.info("TorusGenerator: %d gaussians, R=%.3f, r=%.3f", n, R, r)
        return cloud


# ---------------------------------------------------------------------------
# Random cloud
# ---------------------------------------------------------------------------


class RandomCloudGenerator(Generator):
    """Uniform random Gaussians inside an axis-aligned bounding box.

    Attributes:
        bounds_min: Lower corner of the sampling box.
        bounds_max: Upper corner.
    """

    name: str = "cloud"
    bounds_min: tuple[float, float, float] = (-1.0, -1.0, -1.0)
    bounds_max: tuple[float, float, float] = (1.0, 1.0, 1.0)

    async def generate(self) -> GaussianCloudArrays:
        import numpy as np

        rng = _rng(self.seed)
        n = self.count
        bmin = np.asarray(self.bounds_min, dtype=np.float32)
        bmax = np.asarray(self.bounds_max, dtype=np.float32)
        positions = rng.uniform(bmin, bmax, size=(n, 3)).astype(np.float32)

        cloud = GaussianCloudArrays.empty(n, sh_degree=self.sh_degree)
        extent = float(np.linalg.norm(bmax - bmin))
        local_scale = math.log(max(extent / max(n ** (1.0 / 3.0), 1.0), 1e-6))
        _fill_common(
            cloud.data,
            positions=positions,
            color=self.color,
            opacity=self.opacity,
            base_scale=local_scale,
        )
        log.info("RandomCloudGenerator: %d gaussians in box %s..%s", n, self.bounds_min, self.bounds_max)
        return cloud
