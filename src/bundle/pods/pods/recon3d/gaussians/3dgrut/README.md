# 3DGRUT Pod — Gaussian Ray Tracing & Unscented Transform

Train 3D Gaussian scene representations and export to USD using [NVIDIA 3dgrut](https://github.com/nv-tlabs/3dgrut).

Supports two renderers:
- **3DGUT** (Unscented Transform) — fast rasterization, works on any CUDA GPU
- **3DGRT** (Ray Tracing) — volumetric ray tracing with reflections/refractions, needs RT cores

**Base image:** `thebundle/bases/torch`
**Input:** COLMAP or pyCuSFM output (camera poses + images)
**Output:** trained checkpoint, PLY, USDZ

## Quick Start

```bash
bundle pods build bases
bundle pods build recon3d/gaussians/3dgrut
bundle pods run recon3d/gaussians/3dgrut
```

## Training

### From COLMAP output

```bash
cd src/bundle/pods/pods/recon3d/gaussians/3dgrut
docker compose exec 3dgrut python /opt/3dgrut/train.py \
    --config-name apps/colmap_3dgut.yaml \
    path=/workspace/sfm_output \
    out_dir=/workspace/runs \
    experiment_name=my_scene \
    export_usdz.enabled=true
```

### From pyCuSFM output

```bash
docker compose exec 3dgrut python /opt/3dgrut/train.py \
    --config-name apps/cusfm_3dgut.yaml \
    path=/workspace/sfm_output \
    out_dir=/workspace/runs \
    experiment_name=my_scene \
    export_usdz.enabled=true
```

### With ray tracing (3DGRT)

```bash
docker compose exec 3dgrut python /opt/3dgrut/train.py \
    --config-name apps/colmap_3dgrt.yaml \
    path=/workspace/sfm_output \
    out_dir=/workspace/runs \
    experiment_name=my_scene_rt \
    export_usdz.enabled=true
```

## USD Export

### During training
Add `export_usdz.enabled=true` to any training command (shown above).

### Post-hoc from PLY
```bash
docker compose exec 3dgrut python -m threedgrut.export.scripts.ply_to_usd \
    /workspace/runs/my_scene/model.ply \
    --output_file /workspace/output/scene.usdz
```

## Interactive Viewer

```bash
docker compose exec 3dgrut threedgrut_playground \
    --checkpoint /workspace/runs/my_scene/checkpoint.pth \
    --port 8890
```

Then open `http://localhost:8890` in your browser.

## Available Hydra Configs

| Config | SfM Source | Renderer | Notes |
|--------|-----------|----------|-------|
| `apps/colmap_3dgut.yaml` | COLMAP | 3DGUT (raster) | Default, fast |
| `apps/colmap_3dgrt.yaml` | COLMAP | 3DGRT (ray trace) | Needs RT cores |
| `apps/cusfm_3dgut.yaml` | pyCuSFM | 3DGUT (raster) | Fast SfM path |
| `apps/cusfm_3dgut_mcmc.yaml` | pyCuSFM | 3DGUT + MCMC | Better densification |
| `apps/nerf_synthetic_3dgut.yaml` | NeRF Synthetic | 3DGUT | Blender data |
| `apps/nerf_synthetic_3dgrt.yaml` | NeRF Synthetic | 3DGRT | Blender data |

## Output Structure

```
workspace/runs/my_scene/
├── checkpoint.pth           # Full training checkpoint
├── model.ply                # Gaussian point cloud
├── scene.usdz               # USD export (if enabled)
├── renders/                 # Rendered validation views
└── config.yaml              # Hydra config snapshot
```

## Notes

- GPU enabled via `gpus: all`.
- Port 8890 exposed for the interactive viewer (`threedgrut_playground`).
- `shm_size: 16gb` for large scene training.
- GCC 11 pinned (3dgrut requirement).
- USDZ output compatible with Omniverse Kit 107.3+ and Isaac Sim 5.0.
