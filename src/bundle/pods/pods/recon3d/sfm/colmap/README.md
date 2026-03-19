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
