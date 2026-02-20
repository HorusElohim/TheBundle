# PPISP Pod (CUDA + Torch)

This pod runs PPISP from local source baggage at `tmp/ppisp` and compiles its CUDA extension with Torch available.

It follows PPISP's README guidance:
- install from source
- use `--no-build-isolation`
- build against the same Torch installed in the environment

## Quick Start

```bash
cd src/bundle/pods/pods/ppisp
cp .env.example .env
bundle pods build ppisp
bundle pods run ppisp
bundle pods logs ppisp
```

The startup flow:
1. container boots with CUDA toolkit + Torch preinstalled
2. mounts `tmp/ppisp` at `/opt/ppisp-src`
3. runs `pip install -e /opt/ppisp-src --no-build-isolation`
4. installs local `thebundle` from `/opt/thebundle` (configurable)
5. performs a basic import sanity check for `torch` and `ppisp`

## Notes

- GPU is enabled via `gpus: all`.
- If you need specific architectures, set `TORCH_CUDA_ARCH_LIST` in `.env` (for example `8.9;9.0`).
- The mounted source path is `../../../../../tmp/ppisp` relative to this compose file.
- If you changed pod env/build settings, run `bundle pods build ppisp` again.

## Useful Commands

```bash
bundle pods status ppisp
bundle pods logs ppisp --no-follow
bundle pods down ppisp
```

Enter the container shell (`zsh`):

```bash
cd src/bundle/pods/pods/ppisp
docker compose exec ppisp zsh
```

Fallback (`bash`):

```bash
cd src/bundle/pods/pods/ppisp
docker compose exec ppisp bash
```

## Exec Smoke Test

After `bundle pods run ppisp`, run:

```bash
cd src/bundle/pods/pods/ppisp
docker compose exec ppisp python /workspace/smoke_test.py
```

Expected output includes:
- CUDA availability (`torch.cuda.is_available() == True`)
- successful `ppisp` import
- successful minimal forward pass

Ad-hoc checks:

```bash
cd src/bundle/pods/pods/ppisp
docker compose exec ppisp python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
docker compose exec ppisp python -c "import ppisp; print('PPISP class:', hasattr(ppisp, 'PPISP'))"
```

## Open Dataset Test

You can run PPISP on a public NeRF-style dataset using **Mip-NeRF 360**:

```bash
cd src/bundle/pods/pods/ppisp
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
src/bundle/pods/pods/ppisp/workspace/results
```

Optional lightweight viewer in container:

```bash
cd src/bundle/pods/pods/ppisp
docker compose exec ppisp python -m http.server 8000 -d /workspace
```

Then open:
- `http://localhost:8000/results/frame0_input_output_diff.png`
- `http://localhost:8000/results/novel_views_panel.png`
