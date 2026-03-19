# COLMAP SfM Pod

GPU-accelerated Structure-from-Motion using [COLMAP](https://colmap.github.io/).
Fully unconstrained SfM from images — no initial poses needed.

**Base image:** `thebundle/bases/nvidia`
**Input:** directory of images at `/workspace/images`
**Output:** camera poses + sparse point cloud at `/workspace/sfm_output`

## Quick Start

```bash
bundle pods build recon3d/sfm/colmap
bundle pods run recon3d/sfm/colmap
```

## Testing with the Bicycle Dataset

All recon3d pods share a data volume at `/workspace/data` (host: `src/bundle/pods/pods/recon3d/data/`).
Use `bundle recon3d data` to download benchmark datasets reproducibly.

```bash
# 1. Build and start the pod
bundle pods build recon3d/sfm/colmap
bundle pods up recon3d/sfm/colmap

# 2. Download the Mip-NeRF 360 dataset (shared across all recon3d pods)
docker compose exec colmap bundle recon3d data fetch --dataset 360_v2

# 3. Check available scenes
docker compose exec colmap bundle recon3d data list

# 4. Locate the bicycle scene images
docker compose exec colmap bundle recon3d data locate bicycle

# 5. Run SfM on the bicycle scene
#    First, set up a workspace that points to the dataset images:
docker compose exec colmap bash -c "\
    mkdir -p /workspace/bicycle && \
    ln -sf /workspace/data/360_v2/bicycle/images /workspace/bicycle/images"

docker compose exec colmap bundle recon3d sfm \
    --workspace /workspace/bicycle \
    --backend colmap

# 6. Check status
docker compose exec colmap bundle recon3d status \
    --workspace /workspace/bicycle
```

Expected output:
```
/workspace/bicycle/sfm_output/
├── database.db
└── sparse/
    └── 0/
        ├── cameras.bin      # 194 cameras
        ├── images.bin       # 194 posed images
        └── points3D.bin     # sparse point cloud
```

## Run Automatic Reconstruction

```bash
cd src/bundle/pods/pods/recon3d/sfm/colmap
docker compose exec colmap colmap automatic_reconstructor \
    --workspace_path /workspace/sfm_output \
    --image_path /workspace/images
```

## Step-by-Step Pipeline

```bash
# 1. Feature extraction (GPU-accelerated)
docker compose exec colmap colmap feature_extractor \
    --database_path /workspace/sfm_output/database.db \
    --image_path /workspace/images \
    --SiftExtraction.use_gpu 1

# 2. Feature matching
docker compose exec colmap colmap exhaustive_matcher \
    --database_path /workspace/sfm_output/database.db \
    --SiftMatching.use_gpu 1

# 3. Sparse reconstruction
docker compose exec colmap colmap mapper \
    --database_path /workspace/sfm_output/database.db \
    --image_path /workspace/images \
    --output_path /workspace/sfm_output/sparse

# 4. (Optional) Dense reconstruction
docker compose exec colmap colmap image_undistorter \
    --image_path /workspace/images \
    --input_path /workspace/sfm_output/sparse/0 \
    --output_path /workspace/sfm_output/dense
```

## Output Structure

```
workspace/sfm_output/
├── database.db              # Feature database
├── sparse/
│   └── 0/
│       ├── cameras.bin      # Camera intrinsics
│       ├── images.bin       # Camera poses
│       └── points3D.bin     # Sparse point cloud
└── dense/                   # (optional)
    └── ...
```

## Notes

- GPU enabled via `gpus: all`.
- COLMAP version is configurable via `COLMAP_VERSION` build arg (default: 3.11.1).
- For large datasets, consider using `sequential_matcher` instead of `exhaustive_matcher`.
- Output is compatible with 3dgrut via `apps/colmap_3dgut.yaml` config.
- Dataset volume is shared at `/workspace/data` — download once, use in all recon3d pods.
