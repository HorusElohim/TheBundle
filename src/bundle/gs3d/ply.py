"""3D Gaussian Splatting PLY reader and writer.

The 3DGS PLY layout (as produced by inria-graphdeco/gaussian-splatting,
3DGRUT, gsplat, and most other trainers) stores one vertex per Gaussian
with the following float32 properties:

    x, y, z                  -- centre position
    nx, ny, nz               -- (optional) ignored on read, written as zeros
    f_dc_0, f_dc_1, f_dc_2   -- spherical-harmonics DC term (RGB)
    f_rest_0 .. f_rest_44    -- SH degrees 1..3 (3 channels * 15 coefficients)
    opacity                  -- logit-space opacity
    scale_0, scale_1, scale_2  -- log-space anisotropic scale
    rot_0, rot_1, rot_2, rot_3 -- wxyz quaternion (not normalised)

This module reads/writes that format using a numpy structured array.  The
in-memory container is :class:`GaussianCloudArrays`, a plain dataclass that
exists only to wrap the buffer and provide convenience accessors.  It is
deliberately *not* a :class:`bundle.core.data.Data` subclass — it owns
non-JSON-serialisable arrays.

Numpy is an optional dependency.  Importing this module without numpy
installed will raise a helpful :class:`ImportError` only at call time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bundle.core import logger, tracer

from .data import GaussianCloud

if TYPE_CHECKING:
    import numpy as np

log = logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# Optional numpy import
# ---------------------------------------------------------------------------


def _require_numpy():
    """Import numpy lazily and raise a helpful error if missing."""
    try:
        import numpy as np

        return np
    except ImportError as exc:
        raise ImportError("bundle.gs3d.ply requires numpy. Install with: pip install thebundle[gs3d]") from exc


# ---------------------------------------------------------------------------
# Property layout
# ---------------------------------------------------------------------------


def sh_rest_count(sh_degree: int) -> int:
    """Number of ``f_rest_*`` coefficients for a given SH degree.

    SH degree N has ``(N+1)**2`` coefficients per channel; the DC term
    accounts for one of them.  Three RGB channels gives the total below.
    """
    if sh_degree < 0:
        raise ValueError(f"sh_degree must be >= 0, got {sh_degree}")
    return 3 * ((sh_degree + 1) ** 2 - 1)


def property_names(sh_degree: int) -> list[str]:
    """Ordered PLY property names for a given SH degree."""
    names = ["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"]
    names += [f"f_rest_{i}" for i in range(sh_rest_count(sh_degree))]
    names += ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"]
    return names


def _structured_dtype(sh_degree: int):
    np = _require_numpy()
    return np.dtype([(name, "<f4") for name in property_names(sh_degree)])


# ---------------------------------------------------------------------------
# In-memory container
# ---------------------------------------------------------------------------


@dataclass
class GaussianCloudArrays:
    """In-memory Gaussian splat cloud backed by a numpy structured array.

    This is intentionally not a ``Data`` subclass: it owns numpy buffers
    that should never be JSON-serialised.  Use :func:`write_ply` to persist.

    Attributes:
        data: Structured array with one record per Gaussian.  The dtype is
            built from :func:`property_names` for the requested SH degree.
        sh_degree: SH degree the array was allocated for.
    """

    data: np.ndarray
    sh_degree: int = 3

    @classmethod
    def empty(cls, count: int, sh_degree: int = 3) -> GaussianCloudArrays:
        """Allocate an uninitialised cloud of ``count`` Gaussians."""
        np = _require_numpy()
        arr = np.zeros(count, dtype=_structured_dtype(sh_degree))
        return cls(data=arr, sh_degree=sh_degree)

    def __len__(self) -> int:
        return int(self.data.shape[0])

    @property
    def positions(self) -> np.ndarray:
        """View into ``(N, 3)`` xyz positions."""
        np = _require_numpy()
        return np.stack([self.data["x"], self.data["y"], self.data["z"]], axis=-1)

    def bbox(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Axis-aligned bounding box ``(min_xyz, max_xyz)``."""
        if len(self) == 0:
            zero = (0.0, 0.0, 0.0)
            return zero, zero
        pos = self.positions
        mn = pos.min(axis=0)
        mx = pos.max(axis=0)
        return (float(mn[0]), float(mn[1]), float(mn[2])), (float(mx[0]), float(mx[1]), float(mx[2]))

    def to_metadata(self, path: Path) -> GaussianCloud:
        """Build a :class:`GaussianCloud` metadata record for ``path``."""
        bmin, bmax = self.bbox()
        return GaussianCloud(
            path=path,
            num_gaussians=len(self),
            sh_degree=self.sh_degree,
            bbox_min=bmin,
            bbox_max=bmax,
        )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


@dataclass
class _PlyHeader:
    vertex_count: int
    properties: list[str] = field(default_factory=list)
    binary: bool = True
    little_endian: bool = True
    header_size: int = 0  # bytes consumed in the file (including the trailing newline)

    @property
    def sh_degree(self) -> int:
        rest = sum(1 for name in self.properties if name.startswith("f_rest_"))
        # rest = 3 * ((N+1)^2 - 1)  =>  (N+1)^2 = rest/3 + 1
        per_channel = rest // 3 + 1
        # solve (N+1)^2 = per_channel
        n_plus_one = round(per_channel**0.5)
        return max(0, n_plus_one - 1)


def _parse_header(raw: bytes) -> _PlyHeader:
    """Parse a 3DGS-style binary PLY header from the start of ``raw``."""
    end_marker = b"end_header\n"
    end_idx = raw.find(end_marker)
    if end_idx < 0:
        raise ValueError("Invalid PLY: missing end_header marker")
    header_text = raw[: end_idx + len(end_marker)].decode("ascii", errors="replace")
    lines = header_text.splitlines()

    if not lines or lines[0].strip() != "ply":
        raise ValueError("Invalid PLY: missing magic 'ply' line")

    binary = False
    little_endian = True
    vertex_count = 0
    properties: list[str] = []
    in_vertex = False

    for line in lines[1:]:
        line = line.strip()
        if line.startswith("format"):
            tokens = line.split()
            fmt = tokens[1] if len(tokens) > 1 else ""
            binary = fmt.startswith("binary")
            little_endian = "little" in fmt
        elif line.startswith("element"):
            tokens = line.split()
            in_vertex = len(tokens) >= 3 and tokens[1] == "vertex"
            if in_vertex:
                vertex_count = int(tokens[2])
        elif line.startswith("property") and in_vertex:
            # property <type> <name>
            tokens = line.split()
            if len(tokens) >= 3:
                properties.append(tokens[-1])
        elif line == "end_header":
            break

    return _PlyHeader(
        vertex_count=vertex_count,
        properties=properties,
        binary=binary,
        little_endian=little_endian,
        header_size=end_idx + len(end_marker),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@tracer.Async.decorator.call_raise
async def read_ply_header(path: Path) -> GaussianCloud:
    """Read just the PLY header and return a :class:`GaussianCloud` record.

    This avoids loading the (potentially huge) vertex payload — useful for
    ``bundle gs3d info`` and other tools that only need metadata.
    """
    if not path.exists():
        raise FileNotFoundError(f"PLY file not found: {path}")

    # Read enough bytes to comfortably contain any plausible header.
    with path.open("rb") as fh:
        head = fh.read(64 * 1024)
    header = _parse_header(head)
    log.debug("PLY header: %d vertices, %d properties", header.vertex_count, len(header.properties))
    return GaussianCloud(
        path=path,
        num_gaussians=header.vertex_count,
        sh_degree=header.sh_degree,
    )


@tracer.Async.decorator.call_raise
async def read_ply(path: Path) -> GaussianCloudArrays:
    """Read a 3DGS PLY file fully into a :class:`GaussianCloudArrays`.

    Only binary little-endian PLYs are supported (the universal 3DGS format).
    """
    np = _require_numpy()
    if not path.exists():
        raise FileNotFoundError(f"PLY file not found: {path}")

    with path.open("rb") as fh:
        raw = fh.read()

    header = _parse_header(raw)
    if not header.binary or not header.little_endian:
        raise ValueError(f"Only binary little-endian PLY supported (got binary={header.binary}, le={header.little_endian})")

    sh_degree = header.sh_degree
    expected = property_names(sh_degree)
    if header.properties != expected:
        # The 3DGS layout is fixed; reject mismatched files loudly so callers
        # know to fall back to a different importer rather than reading garbage.
        raise ValueError(
            f"PLY properties do not match the 3DGS layout for sh_degree={sh_degree}.\n"
            f"  expected: {expected}\n  got:      {header.properties}"
        )

    dtype = _structured_dtype(sh_degree)
    payload = raw[header.header_size :]
    expected_bytes = header.vertex_count * dtype.itemsize
    if len(payload) < expected_bytes:
        raise ValueError(f"PLY truncated: expected {expected_bytes} bytes of payload, got {len(payload)}")

    arr = np.frombuffer(payload[:expected_bytes], dtype=dtype).copy()
    log.info("Read PLY: %s (%d Gaussians, sh_degree=%d)", path, len(arr), sh_degree)
    return GaussianCloudArrays(data=arr, sh_degree=sh_degree)


@tracer.Async.decorator.call_raise
async def write_ply(path: Path, arrays: GaussianCloudArrays) -> GaussianCloud:
    """Write a :class:`GaussianCloudArrays` to disk in the 3DGS PLY format.

    Returns the populated :class:`GaussianCloud` metadata record.
    """
    np = _require_numpy()
    path.parent.mkdir(parents=True, exist_ok=True)

    expected_dtype = _structured_dtype(arrays.sh_degree)
    if arrays.data.dtype != expected_dtype:
        raise ValueError(
            f"Array dtype does not match sh_degree={arrays.sh_degree}.\n"
            f"  expected: {expected_dtype}\n  got:      {arrays.data.dtype}"
        )

    header_lines = [
        "ply",
        "format binary_little_endian 1.0",
        f"element vertex {len(arrays)}",
    ]
    header_lines += [f"property float {name}" for name in property_names(arrays.sh_degree)]
    header_lines.append("end_header")
    header = ("\n".join(header_lines) + "\n").encode("ascii")

    payload = np.ascontiguousarray(arrays.data).tobytes()
    with path.open("wb") as fh:
        fh.write(header)
        fh.write(payload)

    log.info("Wrote PLY: %s (%d Gaussians, sh_degree=%d)", path, len(arrays), arrays.sh_degree)
    return arrays.to_metadata(path)
