# bundle.recon3d

3D reconstruction pipeline orchestration — from images/video to Gaussian Splatting to USD.

## Architecture

```
images/ ──► SfM (COLMAP / pyCuSFM) ──► Gaussians (3DGRUT) ──► USD export
```

Each stage is a thin Python wrapper around an external tool. Stages communicate
via **data contracts** — Pydantic models describing filesystem layouts.

## CLI

```bash
# Download benchmark datasets (shared across all recon3d pods)
bundle recon3d data fetch --dataset 360_v2
bundle recon3d data list
bundle recon3d data locate bicycle

# Full pipeline
bundle recon3d run --workspace ./my_scene --sfm-backend colmap --renderer 3dgut

# Individual stages
bundle recon3d sfm       --workspace ./my_scene --backend colmap
bundle recon3d gaussians --workspace ./my_scene --config apps/colmap_3dgut.yaml

# Check pipeline progress
bundle recon3d status --workspace ./my_scene
```

## Workspace Layout

```
workspace/
├── images/                     # Input images
├── sfm_output/
│   ├── database.db
│   └── sparse/0/
│       ├── cameras.bin
│       ├── images.bin
│       └── points3D.bin
├── runs/<experiment>/
│   ├── checkpoint.pth
│   ├── model.ply
│   ├── scene.usdz
│   └── config.yaml
└── manifest.json               # Pipeline state
```

## Shared Data Volume

All recon3d pods mount a shared data directory at `/workspace/data`
(host: `src/bundle/pods/pods/recon3d/data/`). Download once, use everywhere:

```bash
# Inside any recon3d pod:
bundle recon3d data fetch --dataset 360_v2

# The dataset is immediately available in all other pods
# RECON3D_DATA_ROOT env var points to /workspace/data
```

## Usage

### Inside Docker pods

```bash
# Download dataset + run SfM
docker compose exec colmap bundle recon3d data fetch --dataset 360_v2
docker compose exec colmap bash -c "\
    mkdir -p /workspace/bicycle && \
    ln -sf /workspace/data/360_v2/bicycle/images /workspace/bicycle/images"
docker compose exec colmap bundle recon3d sfm --workspace /workspace/bicycle

# Run Gaussians (different pod, same shared data)
docker compose exec 3dgrut bundle recon3d gaussians --workspace /workspace/bicycle
```

### Locally (if dependencies are installed)

```bash
bundle recon3d data fetch --dataset 360_v2 --data-root src/bundle/pods/pods/recon3d/data
bundle recon3d run --workspace ./my_scene
```

Requires COLMAP and/or 3DGRUT to be available on the system.

## SfM Backends

| Backend  | Description                                    | Requires initial poses |
|----------|------------------------------------------------|------------------------|
| `colmap` | GPU-accelerated SIFT features, exhaustive matching, sparse reconstruction | No |
| `pycusfm`| Learned features (ALIKED/SuperPoint) + LightGlue, TensorRT-accelerated   | Yes (optional) |

## Gaussian Renderers

| Renderer | Description                                          | GPU requirement |
|----------|------------------------------------------------------|-----------------|
| `3dgut`  | Unscented Transform rasterization — fast, any CUDA GPU | CUDA            |
| `3dgrt`  | Volumetric ray tracing with reflections/refractions    | RT cores        |

## Contracts

Data contracts define the input/output interface for each stage:

- `Workspace` — root directory with canonical subdirectory layout
- `SfmInput` / `SfmOutput` — images in, sparse reconstruction out
- `GaussiansInput` / `GaussiansOutput` — SfM output in, trained model + PLY out
- `ExportInput` — PLY path + output path for USD export

All contracts inherit from `bundle.core.Data` (Pydantic) and support JSON serialization.
