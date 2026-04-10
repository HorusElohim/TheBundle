"""Mesh-to-Gaussians: surface-sample any trimesh-readable mesh.

The generated splats are *surface-aligned*: each sample becomes a flat,
disc-like Gaussian whose local +Z axis points along the face normal.
``scale_2`` (the normal axis) is small, ``scale_0``/``scale_1`` (the
tangent plane) are larger — the on-disk size of each disc tracks the
average per-sample area ``sqrt(mesh.area / N)`` so coverage stays
roughly uniform regardless of mesh resolution.

If the mesh exposes per-face colours and ``use_mesh_color`` is set,
the SH DC term is sampled from the mesh; otherwise the uniform
``color`` field on the base generator is used.

``trimesh`` is an optional guarded dependency — install via the
``thebundle[gs3d]`` extra.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from bundle.core import logger

from ..ply import GaussianCloudArrays
from .base import Generator
from .primitives import SH_C0

if TYPE_CHECKING:
    import numpy as np

log = logger.get_logger(__name__)


def _require_trimesh():
    """Import trimesh lazily and raise a helpful error if missing."""
    try:
        import trimesh

        return trimesh
    except ImportError as exc:
        raise ImportError("bundle.gs3d.generators.mesh requires trimesh. Install with: pip install thebundle[gs3d]") from exc


def _normals_to_quaternions(normals: np.ndarray) -> np.ndarray:
    """Build wxyz quaternions that rotate local +Z onto each row of ``normals``.

    Normals are expected to be unit length.  The antipodal case (``n ≈ -z``) is
    handled by returning a 180° rotation around the local x axis instead of
    dividing by zero in the half-way formula.
    """
    import numpy as np

    n = normals.astype(np.float32)
    z = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    dot = n @ z  # (N,)
    cross = np.cross(np.broadcast_to(z, n.shape), n)  # (N, 3)

    quats = np.empty((n.shape[0], 4), dtype=np.float32)
    quats[:, 0] = 1.0 + dot
    quats[:, 1:] = cross

    # Antipodal: n ≈ -z → use 180° rotation about x (wxyz = 0,1,0,0).
    antipodal = dot < -0.9999
    quats[antipodal] = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)

    quats /= np.linalg.norm(quats, axis=1, keepdims=True) + 1e-8
    return quats


class MeshToGaussiansGenerator(Generator):
    """Sample a triangle mesh and convert each sample into a surface-aligned Gaussian.

    Attributes:
        source: Path to a trimesh-readable mesh file (obj, ply, stl, glb, ...).
        method: ``"uniform"`` for fast area-weighted sampling, ``"even"`` for
            Poisson-disc-like even sampling (slower).
        disc_thickness_ratio: Ratio of normal-axis scale to tangent-axis scale.
            Smaller values produce thinner, more disc-like splats.
        use_mesh_color: When ``True`` and the mesh exposes per-face colours,
            sample the SH DC term from the mesh instead of using ``color``.
    """

    name: str = "mesh"
    source: Path
    method: Literal["uniform", "even"] = "uniform"
    disc_thickness_ratio: float = 0.1
    use_mesh_color: bool = True

    async def generate(self) -> GaussianCloudArrays:
        import numpy as np

        trimesh = _require_trimesh()

        if not self.source.exists():
            raise FileNotFoundError(f"Mesh file not found: {self.source}")

        mesh = trimesh.load(str(self.source), force="mesh")
        if not isinstance(mesh, trimesh.Trimesh):
            raise TypeError(
                f"Loaded {self.source} is not a single Trimesh "
                f"(got {type(mesh).__name__}). Multi-part scenes are not supported."
            )

        # Sample points on the surface, paired with originating face indices.
        if self.method == "even":
            samples, face_index = trimesh.sample.sample_surface_even(mesh, self.count, seed=self.seed)
            # sample_surface_even may return fewer than requested — top up uniformly.
            shortfall = self.count - len(samples)
            if shortfall > 0:
                extra, extra_face = trimesh.sample.sample_surface(mesh, shortfall, seed=self.seed)
                samples = np.concatenate([samples, extra], axis=0)
                face_index = np.concatenate([face_index, extra_face], axis=0)
        else:
            samples, face_index = trimesh.sample.sample_surface(mesh, self.count, seed=self.seed)

        positions = samples.astype(np.float32)
        normals = mesh.face_normals[face_index].astype(np.float32)

        n_actual = positions.shape[0]
        cloud = GaussianCloudArrays.empty(n_actual, sh_degree=self.sh_degree)
        arr = cloud.data

        arr["x"] = positions[:, 0]
        arr["y"] = positions[:, 1]
        arr["z"] = positions[:, 2]

        # Surface-aligned anisotropic scale: tangent extent ~ sqrt(area / N).
        surface_area = float(mesh.area)
        tangent_extent = math.sqrt(max(surface_area / max(n_actual, 1), 1e-12))
        log_tangent = math.log(max(tangent_extent, 1e-6))
        log_normal = math.log(max(tangent_extent * self.disc_thickness_ratio, 1e-6))
        arr["scale_0"] = log_tangent
        arr["scale_1"] = log_tangent
        arr["scale_2"] = log_normal

        # Rotation: align local +Z with each surface normal.
        quats = _normals_to_quaternions(normals)
        arr["rot_0"] = quats[:, 0]
        arr["rot_1"] = quats[:, 1]
        arr["rot_2"] = quats[:, 2]
        arr["rot_3"] = quats[:, 3]

        arr["opacity"] = self.opacity

        # Colour: per-face mesh colours when available, uniform otherwise.
        coloured = False
        if self.use_mesh_color:
            try:
                face_colors = mesh.visual.face_colors  # (F, 4) uint8
                if face_colors is not None and len(face_colors) >= mesh.faces.shape[0]:
                    rgb = face_colors[face_index, :3].astype(np.float32) / 255.0
                    arr["f_dc_0"] = (rgb[:, 0] - 0.5) / SH_C0
                    arr["f_dc_1"] = (rgb[:, 1] - 0.5) / SH_C0
                    arr["f_dc_2"] = (rgb[:, 2] - 0.5) / SH_C0
                    coloured = True
            except Exception as exc:
                log.debug("MeshToGaussiansGenerator: no usable face colours (%s)", exc)

        if not coloured:
            arr["f_dc_0"] = (self.color[0] - 0.5) / SH_C0
            arr["f_dc_1"] = (self.color[1] - 0.5) / SH_C0
            arr["f_dc_2"] = (self.color[2] - 0.5) / SH_C0

        log.info(
            "MeshToGaussiansGenerator: %d gaussians from %s (method=%s, area=%.3f)",
            n_actual,
            self.source.name,
            self.method,
            surface_area,
        )
        return cloud
