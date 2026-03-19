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

## Usage

### Inside Docker pods

```bash
docker compose exec colmap bundle recon3d sfm --workspace /workspace
docker compose exec 3dgrut bundle recon3d gaussians --workspace /workspace
```

### Locally (if dependencies are installed)

```bash
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
