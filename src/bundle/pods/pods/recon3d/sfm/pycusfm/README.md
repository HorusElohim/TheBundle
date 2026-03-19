# pyCuSFM Pod

GPU-accelerated Structure-from-Motion using [NVIDIA pyCuSFM](https://github.com/nvidia-isaac/pyCuSFM).
5-20x faster than COLMAP with learned features (ALIKED, SuperPoint) + LightGlue matching.

**Base image:** `thebundle/bases/torch-tensorrt`
**Input:** images + initial camera poses in `frames_meta.json`
**Output:** refined camera trajectories + sparse 3D point cloud

## Quick Start

```bash
bundle pods build bases                     # build base chain first
bundle pods build recon3d/sfm/pycusfm
bundle pods run recon3d/sfm/pycusfm
```

## Usage

```bash
cd src/bundle/pods/pods/recon3d/sfm/pycusfm
docker compose exec pycusfm bash
```

Place input data in `workspace/`:
- `workspace/images/` — input image sequence
- `workspace/frames_meta.json` — initial camera poses (6DoF `camera_to_world`)

## Limitations

- **v0.1.8**: Requires initial camera pose estimates as input (no fully unconstrained SfM yet).
  For unconstrained SfM, use the `recon3d/sfm/colmap` pod instead.
- Requires NVIDIA GPU with RT cores recommended (for TensorRT inference).
- Linux only (Docker handles this).

## Output

Output is compatible with 3dgrut via `apps/cusfm_3dgut.yaml` or `apps/cusfm_3dgut_mcmc.yaml` configs.

## Notes

- GPU enabled via `gpus: all`.
- pyCuSFM version is configurable via `PYCUSFM_VERSION` build arg.
- Uses TensorRT for accelerated feature extraction (ALIKED, SuperPoint).
