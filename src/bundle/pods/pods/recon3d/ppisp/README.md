# PPISP Pod (CUDA + Torch)

This pod runs PPISP from local source at `tmp/ppisp` and compiles its CUDA extension with Torch available.

It uses `thebundle/bases/torch` as its base image and follows PPISP's README guidance:
- install from source
- use `--no-build-isolation`
- build against the same Torch installed in the environment

## Quick Start

```bash
cd src/bundle/pods/pods/recon3d/ppisp
cp .env.example .env
bundle pods build recon3d/ppisp
bundle pods run recon3d/ppisp
bundle pods logs recon3d/ppisp
```

The startup flow:
1. container boots with CUDA toolkit + Torch preinstalled (via `thebundle/bases/torch`)
2. mounts `tmp/ppisp` at `/opt/ppisp-src`
3. runs `pip install -e /opt/ppisp-src --no-build-isolation`
4. installs local `thebundle` from `/opt/thebundle` (configurable)
5. performs a basic import sanity check for `torch` and `ppisp`

### Dev mode

Mounts local source for fast iteration — no rebuild needed:

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose --profile dev up ppisp-dev
```

## Notes

- GPU is enabled via `gpus: all`.
- If you need specific architectures, set `TORCH_CUDA_ARCH_LIST` in `.env` (for example `8.9;9.0`).
- If you changed pod env/build settings, run `bundle pods build recon3d/ppisp` again.

## Useful Commands

```bash
bundle pods status recon3d/ppisp
bundle pods logs recon3d/ppisp --no-follow
bundle pods down recon3d/ppisp
```

Enter the container shell (`zsh`):

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose exec ppisp zsh
```

Fallback (`bash`):

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose exec ppisp bash
```

## Exec Smoke Test

After `bundle pods run recon3d/ppisp`, run:

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose exec ppisp python /workspace/smoke_test.py
```

Expected output includes:
- CUDA availability (`torch.cuda.is_available() == True`)
- successful `ppisp` import
- successful minimal forward pass

Ad-hoc checks:

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose exec ppisp python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
docker compose exec ppisp python -c "import ppisp; print('PPISP class:', hasattr(ppisp, 'PPISP'))"
```

## Open Dataset Test

You can run PPISP on a public NeRF-style dataset using **Mip-NeRF 360**:

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose exec ppisp python /workspace/run_dataset.py --scene garden --samples 64 --steps 25 --image-size 256
```

What this test does:
- downloads and extracts `360_v2.zip` from the official Mip-NeRF 360 host into `/workspace/data`
- loads a scene image set (defaults to `garden`)
- runs a short CUDA training loop through `PPISP` with `tqdm` progress
- exports 5 `frame_idx=-1` novel views: `center`, `north`, `south`, `east`, `west`
- writes preview images to `/workspace/results`

Try another scene:

```bash
docker compose exec ppisp python /workspace/run_dataset.py --scene bicycle --samples 96 --steps 40 --image-size 320
```

Train from your own folder directly:

```bash
docker compose exec ppisp python /workspace/run_dataset.py --images-dir /workspace/data/bicycle/images --samples 96 --steps 40 --image-size 320
```

See results from host:

```bash
# Host path:
src/bundle/pods/pods/recon3d/ppisp/workspace/results
```

Optional lightweight viewer in container:

```bash
cd src/bundle/pods/pods/recon3d/ppisp
docker compose exec ppisp python -m http.server 8000 -d /workspace
```

Then open:
- `http://localhost:8000/results/frame0_input_output_diff.png`
- `http://localhost:8000/results/novel_views_panel.png`
