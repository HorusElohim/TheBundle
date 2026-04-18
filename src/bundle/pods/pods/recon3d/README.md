# Recon3D Pods

Docker pods that implement the 3D reconstruction pipeline: real photographs
in, a trained [3D Gaussian Splatting](#3-3d-gaussian-splatting-3dgs) scene
out, ready to view in Blender or export as USD.

Each stage runs in its own container. All pods mount the same
`src/bundle/pods/pods/recon3d/data/` directory at `/workspace/data/` inside
the container, so artefacts flow from one pod to the next without copying.

---

## Table of contents

1. [What this does (and why)](#1-what-this-does-and-why)
2. [Core concepts](#2-core-concepts)
   - [Structure-from-Motion (SfM)](#21-structure-from-motion-sfm)
   - [The PLY file format](#22-the-ply-file-format)
   - [3D Gaussian Splatting (3DGS)](#23-3d-gaussian-splatting-3dgs)
   - [3DGUT vs 3DGRT](#24-3dgut-vs-3dgrt)
   - [USD / USDZ](#25-usd--usdz)
   - [Mip-NeRF 360 dataset](#26-mip-nerf-360-dataset)
3. [Pipeline](#3-pipeline)
4. [Pods](#4-pods)
5. [Prerequisites](#5-prerequisites)
6. [Workspace layout](#6-workspace-layout)
7. [End-to-end: bicycle scene](#7-end-to-end-bicycle-scene)
8. [Starting from scratch (no existing SfM)](#8-starting-from-scratch-no-existing-sfm)
9. [Fetching benchmark data](#9-fetching-benchmark-data)
10. [Direct pod use & troubleshooting](#10-direct-pod-use--troubleshooting)
11. [Final tutorial: bicycle, end-to-end](#11-final-tutorial-bicycle-end-to-end)

---

## 1. What this does (and why)

Given a folder of ordinary photographs of a static scene (say, 100–300 images
of a bicycle taken from different angles), this pipeline produces a
**photorealistic 3D model** that you can view from any viewpoint, re-render
under different lighting in Blender, or export to USD for Omniverse / Isaac
Sim / AR.

The two big steps are:

1. **Recover the camera geometry** — for every image, figure out where the
   camera was and which direction it was pointing. This is
   [SfM](#21-structure-from-motion-sfm).
2. **Fit a volumetric scene representation** — train a cloud of tiny
   coloured, oriented, semi-transparent 3D blobs ("Gaussians") that, when
   rendered from each known camera, reproduce the original photos. This is
   [3D Gaussian Splatting](#23-3d-gaussian-splatting-3dgs).

The scene file is a [PLY](#22-the-ply-file-format) with millions of
Gaussians; rendering it from a new viewpoint is fast enough to be real-time
on a modern GPU.

---

## 2. Core concepts

### 2.1. Structure-from-Motion (SfM)

**SfM** takes an unordered pile of images and recovers:

- **Camera intrinsics** — focal length, principal point, lens distortion
  (one model per camera, or one per image for uncalibrated captures).
- **Camera extrinsics (poses)** — the 6-DoF rotation + translation of each
  camera relative to a shared world frame.
- **A sparse 3D point cloud** — the 3D positions of feature points (corners,
  textures) that were matched across multiple images.

How it works, in one paragraph: detect 2D feature points in each image
(SIFT, SuperPoint, etc.), match them across image pairs, estimate the
essential matrix between pairs to recover relative rotation + translation,
then triangulate matched points to 3D and bundle-adjust everything
simultaneously to minimise reprojection error.

Two SfM backends are available in this repo:

- **[COLMAP](https://colmap.github.io/)** — the reference open-source SfM
  pipeline. Robust, deterministic, CPU-dominated with optional CUDA feature
  matching. This is the default.
- **[pyCuSFM](https://github.com/nv-tlabs/3dgrut)** — NVIDIA's CUDA-native
  SfM. Faster on GPU-heavy workloads; used by 3dgrut's `cusfm_*` configs.

**Output:** `sfm_output/sparse/0/` containing `cameras.bin`, `images.bin`,
`points3D.bin` (COLMAP's binary format).

### 2.2. The PLY file format

**PLY** (Polygon File Format, a.k.a. Stanford Triangle Format) is a simple
3D-data container. A PLY file has:

- An **ASCII header** declaring element types (`vertex`, `face`, …) and
  which named, typed **properties** each element carries.
- A **body** (ASCII or little-endian binary) with one row of values per
  element in the order declared.

Classical PLY stores vertices (`x y z`), optionally with colours
(`red green blue`) and faces. It's extensible — you can declare arbitrary
custom per-vertex properties, and that's exactly what 3DGS does.

**3DGS-flavoured PLY** stores one Gaussian per "vertex", with these extra
per-vertex properties (standard INRIA layout):

| Property | Count | Meaning |
|---|---|---|
| `x`, `y`, `z`                | 3  | Gaussian centre (mean) |
| `nx`, `ny`, `nz`             | 3  | Normal (unused by 3DGS, kept for compatibility) |
| `f_dc_0`, `f_dc_1`, `f_dc_2` | 3  | View-independent RGB colour (0th-order spherical harmonic) |
| `f_rest_0` … `f_rest_44`     | 45 | Higher-order spherical-harmonic colour coefficients (SH degree 3: 15 coeffs × 3 channels) |
| `opacity`                    | 1  | Log-odds alpha (sigmoid to get [0, 1]) |
| `scale_0`, `scale_1`, `scale_2` | 3 | Log-scale per principal axis (exp to get metric scale) |
| `rot_0`, `rot_1`, `rot_2`, `rot_3` | 4 | Orientation quaternion `(w, x, y, z)` |

So each Gaussian is 62 floats. A typical trained scene has 0.5–5 million
Gaussians → tens to hundreds of MB per PLY.

Other variants you may encounter: `.splat` (compact quantised binary from
antimatter15), `.ksplat` (SuperSplat), `.spz` (Niantic). This repo sticks
to the standard PLY layout.

### 2.3. 3D Gaussian Splatting (3DGS)

Introduced by Kerbl et al. (SIGGRAPH 2023), 3DGS represents a scene as a
cloud of **3D Gaussians**, each defined by:

- a 3D mean (position),
- a 3×3 covariance matrix (parameterised as `scale` + `rotation` for
  stability),
- an opacity α,
- view-dependent colour encoded as spherical harmonics.

**Rendering** ("splatting"): project each 3D Gaussian to a 2D screen-space
ellipse, sort front-to-back per tile, and alpha-blend. This is a
differentiable rasteriser, so gradients flow back to every Gaussian's
position, shape, colour, and opacity.

**Training**: initialise from the SfM sparse point cloud; for each known
camera, render the current Gaussians, compare to the real photo (L1 + SSIM
loss), backpropagate, and periodically **densify** (split/clone Gaussians
where error is high) and **prune** (delete near-transparent ones). After
~30k iterations you have a scene that renders novel views at 30–100 FPS.

3DGS beats NeRFs on speed (real-time vs seconds/frame) and matches or
exceeds them on quality, which is why it took over the field.

### 2.4. 3DGUT vs 3DGRT

Both come from NVIDIA's [`nv-tlabs/3dgrut`](https://github.com/nv-tlabs/3dgrut)
repo and this pod supports both.

- **3DGUT — 3D Gaussian Unscented Transform.** Replaces the original 3DGS
  EWA ("Elliptical Weighted Average") projection with the Unscented
  Transform: each Gaussian is approximated by a handful of *sigma points*
  that are projected through the camera model exactly, then a 2D conic is
  fitted to them. This makes it robust to **distorted cameras** (fisheye,
  wide-angle) and **rolling-shutter** phones — the original 3DGS assumes a
  pinhole camera. Still rasterisation, still real-time.
- **3DGRT — 3D Gaussian Ray Tracing.** Replaces rasterisation with actual
  ray tracing of the Gaussian particles, giving you secondary effects that
  splatting can't do: true reflections, refractions (glass, water),
  shadows, depth-of-field. Slower; benefits strongly from RT-core GPUs.

The two are complementary — 3DGUT for primary rays (fast, distortion-aware)
and 3DGRT for secondary rays (reflections off a splatted scene). The pod
exposes both via Hydra configs.

| Config | Renderer | Use when |
|---|---|---|
| `apps/colmap_3dgut.yaml` | 3DGUT | default, pinhole/fisheye COLMAP input |
| `apps/colmap_3dgrt.yaml` | 3DGRT | you want reflective/refractive effects |
| `apps/cusfm_3dgut.yaml`  | 3DGUT | pyCuSFM input |
| `apps/cusfm_3dgut_mcmc.yaml` | 3DGUT + MCMC | better densification on sparse scenes |
| `apps/nerf_synthetic_3dgut.yaml` | 3DGUT | NeRF-Synthetic Blender data |
| `apps/nerf_synthetic_3dgrt.yaml` | 3DGRT | NeRF-Synthetic, ray-traced |

### 2.5. USD / USDZ

**USD** (Universal Scene Description, Pixar) is the open scene-graph format
used by Omniverse, Isaac Sim, RealityKit, and many DCC tools. **USDZ** is a
zero-compression zip archive of a USD + its textures, analogous to a
self-contained `.glb` for the USD ecosystem (used by Apple Quick Look / AR).

3dgrut can export a trained scene to USDZ for downstream use. Pass
`export_usdz.enabled=true` to `train.py` or run the post-hoc
`threedgrut.export.scripts.ply_to_usd` script.

### 2.6. Mip-NeRF 360 dataset

The standard benchmark for unbounded real-world reconstruction: 7 scenes
(`bicycle`, `bonsai`, `counter`, `garden`, `kitchen`, `room`, `stump`),
each ~100–300 images at ~4k resolution, captured with a phone. The
`data/bicycle/` tree in this repo is one of those scenes, with COLMAP SfM
already pre-computed. Fetch the others with `bundle recon3d data fetch
--dataset 360_v2` (see [§9](#9-fetching-benchmark-data)).

---

## 3. Pipeline

```
  images/  ──►  SfM  ──►  sfm_output/  ──►  Gaussians  ──►  runs/<exp>/*.ply  ──►  Blender / USD
              (colmap)                      (3dgrut)                                (local, no pod)
              (pycusfm)                     (opensplat)
```

| Stage | Input | Output | Produced by |
|---|---|---|---|
| SfM       | `images/`                           | `sfm_output/sparse/0/`  | `sfm/colmap` or `sfm/pycusfm` |
| Gaussians | `images/` + `sfm_output/`           | `runs/<exp>/model.ply`, `checkpoint.pth` | `gaussians/3dgrut` or `gaussians/opensplat` |
| Blender   | `runs/<exp>/model.ply`              | `.blend` scene, PNG renders | `bundle gs3d blender` (host, no pod) |
| USD       | `runs/<exp>/model.ply` or checkpoint | `export/*.usdz`         | `gaussians/3dgrut` (post-hoc) |

---

## 4. Pods

| Pod | Role | GPU | Base image | Details |
|---|---|---|---|---|
| [`sfm/colmap`](sfm/colmap/README.md)       | Structure-from-Motion (COLMAP)  | CUDA (or `Dockerfile.cpu`) | `thebundle/bases/nvidia` | Default SfM |
| [`sfm/pycusfm`](sfm/pycusfm/README.md)     | Structure-from-Motion (pyCuSFM) | CUDA         | `thebundle/bases/torch` | Faster CUDA-native alternative |
| [`gaussians/3dgrut`](gaussians/3dgrut/README.md) | 3DGS training + USDZ export | CUDA     | `thebundle/bases/torch` | NVIDIA 3dgrut ([3DGUT / 3DGRT](#24-3dgut-vs-3dgrt)) |
| [`gaussians/fastergs`](gaussians/fastergs/README.md) | Faster-GS 3DGS training (experimental) | CUDA | `thebundle/bases/torch` | [Faster-GS](https://github.com/nerficg-project/faster-gaussian-splatting) — ~3–5× speedup |
| `gaussians/opensplat`                      | 3DGS training (cross-platform)  | CUDA / Metal / CPU | — | Lightweight fallback |
| [`ppisp`](ppisp/README.md)                 | Image preprocessing (white-balance, etc.) | — | — | Optional step before SfM |

---

## 5. Prerequisites

- **Docker** with the NVIDIA container runtime. On WSL2: install Docker
  Desktop on Windows and enable **Settings → Resources → WSL integration**
  for your distro. Verify with:
  ```bash
  docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
  ```
- **RTX-class GPU** (RTX 2060 or newer recommended; 3DGRT really wants RT
  cores). 12 GB VRAM minimum for Mip-NeRF 360 scenes; 24 GB is comfortable.
- **Disk**: ~20 GB for the base + 3dgrut images, ~15 GB for Mip-NeRF 360
  data, 0.5–2 GB per trained scene.
- Build the base images once, then the per-stage pods you need:
  ```bash
  bundle pods build bases                       # thebundle/bases/{cpu,nvidia,torch}
  bundle pods build recon3d/sfm/colmap          # SfM (default)
  bundle pods build recon3d/gaussians/3dgrut    # Gaussian training
  ```
  First build of `3dgrut` is ~10–20 min (clones the upstream repo and
  compiles CUDA kernels). Inspect what's available with `bundle pods list`
  or `docker images`.

---

## 6. Workspace layout

Each scene lives in its own folder under [`data/`](data/):

```
data/<scene>/
├── images/              # full-resolution source photos (SfM input)
├── images_2/4/8/        # optional 2×/4×/8× downsampled variants (Mip-NeRF 360 ships these)
├── sfm_output/          # written by sfm/* pods
│   ├── database.db      # COLMAP's feature + match DB
│   ├── sparse/0/        # cameras.bin, images.bin, points3D.bin
│   └── undistorted/     # radial-distortion-corrected images (for training)
├── runs/<experiment>/   # written by gaussians/* pods
│   ├── model.ply        # trained 3DGS scene (see §2.2)
│   ├── checkpoint.pth   # full trainer state (resume / viewer)
│   ├── renders/         # validation renders per iteration
│   └── config.yaml      # Hydra config snapshot
├── export/              # USD / USDZ output
└── manifest.json        # pipeline state (written by bundle recon3d run)
```

**Volume mount inside containers:** this whole `data/` tree is mounted at
`/workspace/data/` — so inside the 3dgrut container the bicycle scene is
at `/workspace/data/bicycle/…`, not `/workspace/bicycle/…`. Pay attention
to this when writing commands.

---

## 7. End-to-end: bicycle scene

The `data/bicycle/` workspace already contains `images/` (194 photos) and a
pre-computed `sfm_output/sparse/0/`, so you can skip straight to training.

### 7.1. Train Gaussians (3dgrut, ~30 min – 2 h on a 3090)

Training runs **inside the 3dgrut pod**, not in the host venv. The
`bundle recon3d gaussians` CLI is the local-install path and will abort
with `Stage 'gaussians.3dgrut' is not available on this system` unless
`threedgrut` is importable in your venv — which it normally isn't. Use the
pod flow below.

Build and start the pod (one-time):

```bash
bundle pods build bases                       # if not already built
bundle pods build recon3d/gaussians/3dgrut
bundle pods up recon3d/gaussians/3dgrut
```

Run training. 3dgrut's COLMAP loader resolves `images/` and `sparse/0/`
**relative to `path=`**, so `path=` must point at a directory that contains
both — which for Mip-NeRF 360 scenes is the scene root, not the nested
`sfm_output/`. The `data/` tree is mounted at `/workspace/data/`:

```bash
bundle pods exec recon3d/gaussians/3dgrut -- \
    python /opt/3dgrut/train.py \
        --config-name apps/colmap_3dgut.yaml \
        path=/workspace/data/bicycle \
        out_dir=/workspace/data/bicycle/runs \
        experiment_name=default
```

**What happens:** Hydra loads `apps/colmap_3dgut.yaml`, 3dgrut reads the
COLMAP `sfm_output`, initialises Gaussians from the SfM sparse cloud, and
trains for ~30k iterations while writing intermediate renders and a final
`model.ply` + `checkpoint.pth`.

Output lands at `data/bicycle/runs/default/model.ply` on the host.

Swap `colmap_3dgut.yaml` → `colmap_3dgrt.yaml` to use ray tracing instead
(slower, supports reflections/refractions — see [§2.4](#24-3dgut-vs-3dgrt)).

### 7.2. View in Blender

```bash
find src/bundle/pods/pods/recon3d/data/bicycle/runs -name "*.ply"

bundle gs3d blender <path-to-ply> \
    -o /tmp/bicycle.blend \
    --render --engine CYCLES
```

This imports the PLY, builds a Geometry-Nodes tree that renders each
Gaussian centre as a small emissive sphere, and (with `--render`) produces
a preview PNG. For a proper real-time 3DGS viewer instead of Blender's
approximation, drop the PLY into <https://superspl.at/>.

### 7.3. Interactive 3dgrut viewer (optional, extra setup)

`/opt/3dgrut/playground.py` depends on [NVIDIA Kaolin](https://kaolin.readthedocs.io/),
which ships as torch/CUDA-version-specific wheels from NVIDIA's S3 index —
**not** the PyPI `kaolin` placeholder. The Dockerfile in this repo does
not install it, so the playground is not usable out of the box. If you
need it, install the matching Kaolin wheel inside the container (pick the
URL for your torch+CUDA from <https://kaolin.readthedocs.io/en/latest/notes/installation.html>),
then:

```bash
bundle pods up recon3d/gaussians/3dgrut
bundle pods exec recon3d/gaussians/3dgrut -- \
    python /opt/3dgrut/playground.py \
        --checkpoint /workspace/data/bicycle/runs/default/checkpoint.pth \
        --port 8890
```

Browse <http://localhost:8890>. For a viewer that **works today**, use
step 7.2 (Blender) or <https://superspl.at/>.

---

## 8. Starting from scratch (no existing SfM)

Replace step 7.1 with the full pipeline:

```bash
bundle recon3d run \
    --workspace src/bundle/pods/pods/recon3d/data/<scene> \
    --sfm-backend colmap \
    --renderer 3dgut \
    --blender \
    --no-visualize \
    --no-export-usdz
```

`bundle recon3d run` chains SfM → Gaussians → Blender, writing a
`manifest.json` that records which stage produced what. Add
`--export-usdz` to also produce `export/<scene>.usdz`.

---

## 9. Fetching benchmark data

```bash
bundle recon3d data fetch --dataset 360_v2 --data-root src/bundle/pods/pods/recon3d/data
bundle recon3d data list
bundle recon3d data locate --scene garden
```

[Mip-NeRF 360](#26-mip-nerf-360-dataset) (~14 GB) unpacks flat:
`bicycle/`, `bonsai/`, `counter/`, `garden/`, `kitchen/`, `room/`, `stump/`
— all with images + pre-computed COLMAP SfM, so you can go straight to
training for any of them.

---

## 10. Direct pod use & troubleshooting

Each pod is runnable on its own; see the per-pod README for the
container-side commands (`colmap feature_extractor`, `python /opt/3dgrut/train.py`,
etc.). The `bundle recon3d ...` commands above are thin orchestrators over
those same calls.

**Common errors and fixes:**

| Symptom | Cause | Fix |
|---|---|---|
| `Stage 'gaussians.3dgrut' is not available on this system.` | You called `bundle recon3d gaussians`, which needs `threedgrut` in the *host* venv. | Use the pod flow in [§7.1](#71-train-gaussians-3dgrut-30-min--2-h-on-a-3090). |
| `FileNotFoundError: .../sparse/0/images.bin` or `.../images/*.JPG` inside the 3dgrut container | `path=` must point at a directory that contains **both** `images/` and `sparse/0/`. | For Mip-NeRF 360, that's the scene root: `path=/workspace/data/<scene>`, not `<scene>/sfm_output`. |
| `ModuleNotFoundError: No module named 'kaolin'` (or the PyPI kaolin placeholder raising `ImportError`) | The 3dgrut playground requires NVIDIA Kaolin (not on PyPI). | Install the Kaolin wheel that matches your torch+CUDA from NVIDIA's S3 index, or skip the playground — use Blender ([§7.2](#72-view-in-blender)) instead. |
| `failed to get console: provided file is not a console` during `bundle pods build` | BuildKit TTY progress writer clashing with piped stdout in `ProcessStream` (`--ansi always`). | See the open note in `src/bundle/pods/manager.py` lines 334 / 428 — drop `--ansi always`, use `--progress plain` for `build`. |
| `OCI runtime exec failed: exec: "<name>": executable file not found in $PATH` | Upstream README references a binary that was never installed. | Inside 3dgrut, most entrypoints are plain scripts: `python /opt/3dgrut/playground.py`, `python /opt/3dgrut/train.py`. |

---

## 11. Final tutorial: bicycle, end-to-end

This is a single, copy-pasteable walkthrough for the Mip-NeRF 360 `bicycle`
scene that ships pre-configured in `data/bicycle/`. It uses `bundle pods`
to manage the container and `bundle` itself for the host-side Blender step.
All commands run from the repo root with the venv active (`source
venv/bin/activate`).

### Step 0 — Sanity checks (one-off)

```bash
# GPU visible inside Docker?
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# Scene present? Expect: images/ images_[248]/ sfm_output/ …
ls src/bundle/pods/pods/recon3d/data/bicycle/

# Pre-computed SfM present? Expect: cameras.bin images.bin points3D.bin
ls src/bundle/pods/pods/recon3d/data/bicycle/sfm_output/sparse/0/
```

If any of the three fails, fix it before continuing: enable Docker's WSL
integration, or run `bundle recon3d data fetch --dataset 360_v2
--data-root src/bundle/pods/pods/recon3d/data` to grab the dataset.

### Step 1 — Build images (one-off, ~10–20 min)

```bash
bundle pods build bases                    # thebundle/bases/{cpu,nvidia,torch}
bundle pods build recon3d/gaussians/3dgrut # clones upstream 3dgrut, compiles CUDA
```

Verify:

```bash
bundle pods list
docker images | grep thebundle
```

You should see `thebundle/recon3d/gaussians/3dgrut:latest`.

### Step 2 — Start the 3dgrut pod

```bash
bundle pods run recon3d/gaussians/3dgrut   # detached (keeps running)
bundle pods status recon3d/gaussians/3dgrut
```

The pod's `command` is `sleep infinity`, so it idles; we exec into it for
training. If you prefer to see logs streaming, use
`bundle pods up recon3d/gaussians/3dgrut` instead (foreground).

### Step 3 — Train Gaussians (~30 min – 2 h on a 3090)

```bash
bundle pods exec recon3d/gaussians/3dgrut -- \
    python /opt/3dgrut/train.py \
        --config-name apps/colmap_3dgut.yaml \
        path=/workspace/data/bicycle \
        out_dir=/workspace/data/bicycle/runs \
        experiment_name=default
```

Watch progress (separate terminal):

```bash
bundle pods logs recon3d/gaussians/3dgrut --tail 200
```

When the run finishes you should have, on the host:

```
src/bundle/pods/pods/recon3d/data/bicycle/runs/default/
├── model.ply          # the trained 3D Gaussian Splatting scene
├── checkpoint.pth     # trainer state (resume / viewer)
├── config.yaml        # Hydra config snapshot
└── renders/           # per-iteration validation PNGs
```

### Step 4 — Inspect the PLY

```bash
# Quick header read (no array payload loaded — just counts + bbox)
bundle gs3d info src/bundle/pods/pods/recon3d/data/bicycle/runs/default/model.ply
```

You should see something like ~1–3M Gaussians and a bbox spanning several
metres. If the count is suspiciously low (<100k) the training probably
crashed early — check the pod logs.

### Step 5 — View in Blender

```bash
bundle gs3d blender \
    src/bundle/pods/pods/recon3d/data/bicycle/runs/default/model.ply \
    --blend-output /tmp/bicycle.blend \
    --render --engine CYCLES
```

This runs Blender headlessly to:
1. import the PLY,
2. build a Geometry-Nodes tree that instances a tiny emissive icosphere at
   each Gaussian centre (so the points are actually shadeable),
3. render one preview PNG with CYCLES,
4. save `/tmp/bicycle.blend`.

Open `/tmp/bicycle.blend` in a GUI Blender to navigate the scene, or for a
proper real-time 3DGS viewer drag `model.ply` into <https://superspl.at/>.

### Step 6 — (Optional) Export to USDZ

Re-train with USDZ enabled, or post-hoc from the PLY:

```bash
bundle pods exec recon3d/gaussians/3dgrut -- \
    python -m threedgrut.export.scripts.ply_to_usd \
        /workspace/data/bicycle/runs/default/model.ply \
        --output_file /workspace/data/bicycle/export/bicycle.usdz
```

Output lands at `data/bicycle/export/bicycle.usdz` on the host — drop it
into Omniverse, Isaac Sim, or Apple Quick Look.

### Step 7 — Cleanup

```bash
bundle pods down recon3d/gaussians/3dgrut   # stop + remove the container
```

The pod image stays cached; you don't rebuild next time. Training outputs
stay under `data/bicycle/runs/` on the host.

### Recap — one-liner mental model

```
bundle pods build …         → container with 3dgrut CUDA env
bundle pods run  …          → idle container, workspace mounted
bundle pods exec … train.py → SfM → Gaussians, writes model.ply
bundle gs3d info model.ply  → sanity-check the trained scene
bundle gs3d blender …       → .blend + PNG, ready to view / render
bundle pods down …          → stop the container
```

From here you can swap `bicycle` for any other Mip-NeRF 360 scene
(`garden`, `kitchen`, …) or point `path=` at your own photos after running
the `sfm/colmap` pod first.
