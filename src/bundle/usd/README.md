# bundle.usd

OpenUSD scene building and export utilities.

A standalone module for working with USD/USDZ files — reusable beyond 3D reconstruction
(simulation, robotics, digital twins, etc.).

## CLI

```bash
# Convert PLY point cloud to USDZ
bundle usd export --input ./model.ply --output ./scene.usdz
```

## Export Backends

The exporter tries backends in order:

1. **3DGRUT** — when running inside the Gaussians pod, delegates to
   `threedgrut.export.scripts.ply_to_usd` which handles Gaussian-specific
   attributes (opacity, spherical harmonics, covariances).

2. **pxr (OpenUSD)** — standalone export via the `usd-core` Python package.
   Install with `pip install thebundle[usd]`.

## Python API

```python
from bundle.usd.export import ply_to_usdz
from bundle.usd.ply import read_ply_info

# Inspect a PLY file
info = await read_ply_info(Path("model.ply"))
print(f"{info.vertex_count} vertices, colors={info.has_colors}")

# Export to USDZ
output = await ply_to_usdz(Path("model.ply"), Path("scene.usdz"))
```

## Installation

```bash
# Minimal (requires 3DGRUT or pxr to be available)
pip install thebundle

# With standalone USD support
pip install thebundle[usd]
```
