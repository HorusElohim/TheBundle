# Faster-GS Pod — Faster Gaussian Splatting

Train a 3D Gaussian Splatting scene with [Faster-GS](https://github.com/nerficg-project/faster-gaussian-splatting)
(CVPR 2026), wrapped in the NeRFICG framework. Targets 3–5× faster training
than vanilla 3DGS with comparable quality — a practical middle ground
between full-fidelity 3dgrut and real-time-iteration tooling like FastGS.

**Status:** experimental scaffold. The pod builds and exposes a
`train_fastergs.py` wrapper that mirrors the CLI shape of 3dgrut's
`train.py`; quality/iteration knobs and config-level tuning will be fleshed
out once a reference run is validated.

**Base image:** `thebundle/bases/torch`
**Input:** COLMAP output (scene root with `images/` + `sparse/0/`)
**Output:** trained checkpoint, PLY

## Quick Start

```bash
bundle pods build bases
bundle pods build recon3d/gaussians/fastergs
bundle pods run recon3d/gaussians/fastergs
```

## Training

```bash
bundle pods exec recon3d/gaussians/fastergs -- \
    python /opt/train_fastergs.py \
        --path /workspace/data/bicycle \
        --out-dir /workspace/data/bicycle/runs \
        --experiment fastergs_default
```

Output PLY is surfaced as
`/workspace/data/bicycle/runs/fastergs_default/model.ply` (the wrapper copies
the first `.ply` NeRFICG emits under the experiment dir to the canonical
`model.ply` name used by the rest of the pipeline).

## Notes

- NeRFICG is YAML-config-driven; the wrapper generates a config via
  `scripts/create_config.py -m FasterGS -d Colmap` and patches in the dataset
  path + output directory before invoking `scripts/train.py`. For fine
  tuning, exec into the container and edit
  `/opt/nerficg/configs/<experiment>_fastergs.yaml` directly, then re-run
  `python scripts/train.py -c configs/<experiment>_fastergs.yaml`.
- Port 8890 is not exposed — Faster-GS does not ship an interactive viewer
  analogous to 3dgrut's playground. Use `bundle gs3d blender <model.ply>`
  or <https://superspl.at/> to inspect results.
