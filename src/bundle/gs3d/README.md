# bundle.gs3d — Synthetic 3D/4D Gaussian Splatting

Procedural generation of Gaussian splat clouds — no cameras, no training, no CUDA required.  
Output is the standard 3DGS binary PLY format, compatible with every viewer and downstream stage in TheBundle.

---

## Architecture

```
bundle.gs3d
├── data.py          GaussianCloud / GaussianSequence  (pure metadata, JSON-serialisable)
├── ply.py           read_ply / write_ply / read_ply_header
├── temporal.py      TemporalGenerator — static PLY → keyframed 4D sequence
├── bridge.py        GaussianCloud → GaussiansOutput  (one-way bridge to recon3d)
├── cli.py           bundle gs3d generate / info / animate
└── generators/
    ├── base.py      Generator(Entity) — shared fields (count, sh_degree, seed, …)
    ├── primitives.py  Sphere · Cube · Torus · RandomCloud
    └── mesh.py      MeshToGaussiansGenerator  (trimesh, optional)
```

`bundle.gs3d` is a **sibling** of `bundle.recon3d`.  
The data flows one way: `gs3d` → `GaussiansOutput` → Blender / USD / visualization.  
`recon3d` never imports `gs3d`.

---

## CLI quick-start

```bash
# Sphere — 50 k Gaussians on a unit sphere
bundle gs3d generate --shape sphere --count 50000 --output sphere.ply

# Coloured cube (volume)
bundle gs3d generate --shape cube --size 2.0 --no-surface --color 0.8,0.4,0.2 --output cube.ply

# Torus
bundle gs3d generate --shape torus --major-radius 1.5 --minor-radius 0.4 --output torus.ply

# Uniform random cloud inside a box
bundle gs3d generate --shape cloud --count 20000 --output cloud.ply

# Mesh → Gaussians (requires: pip install trimesh)
bundle gs3d generate --shape mesh --source model.obj --count 100000 --output mesh.ply

# Header-only inspection (no array load)
bundle gs3d info sphere.ply

# 4D orbit animation — 60 frames at 30 fps
bundle gs3d animate --input sphere.ply --motion orbit --frames 60 --output-dir ./seq/
```

---

## Python API

```python
import asyncio
from pathlib import Path
from bundle.gs3d.generators import SphereGenerator, create_generator
from bundle.gs3d.ply import write_ply, read_ply_header

async def main():
    # Instantiate via class
    cloud = await SphereGenerator(count=10_000, radius=1.5, seed=42).generate()

    # Or via factory
    cloud = await create_generator("torus", count=5_000, major_radius=2.0).generate()

    meta = await write_ply(Path("/tmp/out.ply"), cloud)
    print(meta.num_gaussians, meta.sh_degree, meta.bbox_min)

    head = await read_ply_header(Path("/tmp/out.ply"))
    print(head)  # GaussianCloud(path=…, num_gaussians=…, sh_degree=…)

asyncio.run(main())
```

---

## 4D sequences

```python
from bundle.gs3d.temporal import MotionConfig, TemporalGenerator

seq = await TemporalGenerator(
    ply_path=Path("sphere.ply"),
    motion=MotionConfig(motion_type="orbit", amplitude=1.0, frequency=0.5, axis="y"),
    frame_count=60,
    fps=30.0,
    output_dir=Path("/tmp/seq"),
).generate()

print(seq.frame_count, seq.frame_paths[0])
```

---

## Generators

| Shape | Key parameters | Notes |
|-------|---------------|-------|
| `sphere` | `radius`, `surface` | Surface: uniform on S², Volume: r ~ U^(1/3) |
| `cube`   | `size`, `surface` | Surface: per-face uniform; Interior: uniform box |
| `torus`  | `major_radius`, `minor_radius` | Parametric (u,v) sampling |
| `cloud`  | `bounds_min`, `bounds_max` | Uniform AABB |
| `mesh`   | `source`, `method` | Surface-aligned splats; requires `trimesh` |

All generators share: `count`, `sh_degree`, `seed`, `opacity`, `color`.

---

## Optional dependencies

```bash
pip install numpy          # required for all generators
pip install trimesh        # required only for --shape mesh
```

Or install the full extra: `pip install thebundle[gs3d]`
