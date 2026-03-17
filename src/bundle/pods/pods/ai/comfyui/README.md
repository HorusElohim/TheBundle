# ComfyUI Pod (Fast, Minimal, NVIDIA-Only)

This pod builds ComfyUI from source on top of a slim Python base image and keeps runtime automation minimal.
Goal: predictable builds, fast restarts, and persistent local data.

## What this setup optimizes

- Reproducible local image builds from a pinned `COMFYUI_VERSION`.
- One-time custom node bootstrap with a marker file.
- Persistent host volumes for models, inputs, outputs, cache, and user state.
- Minimal runtime extras (`git` and `ffmpeg`) for common video workflows.

## Quick Start

```bash
cd src/bundle/pods/pods/ai/comfyui
cp .env.example .env
bundle pods build ai/comfyui
bundle pods run ai/comfyui
bundle pods logs ai/comfyui
```

Open `http://localhost:8188`.

### Dev mode

Mounts local source for fast iteration — no rebuild needed:

```bash
cd src/bundle/pods/pods/ai/comfyui
docker compose --profile dev up comfyui-dev
```

## Automation on First Startup

When `INSTALL_CUSTOM_NODES=1`, startup installs selected custom node repositories into `data/custom_nodes` and can install their Python dependencies.

Default node list:
- `comfyui-manager`
- `ComfyUI-VideoHelperSuite`
- `ComfyUI-AnimateDiff-Evolved`
- `ComfyUI-CogVideoXWrapper`
- `ComfyUI-LTXVideo`
- `ComfyUI-WanVideoWrapper`

## Data Layout

Persistent runtime data lives under `src/bundle/pods/pods/ai/comfyui/data`:
- `models`
- `input`
- `output`
- `custom_nodes`
- `user`
- `cache`
- `user_db`

Important model subfolders under `data/models` are created automatically, including:
`checkpoints`, `diffusion_models`, `text_encoders`, `clip_vision`, `vae`, `CogVideo`, `loras`, `latent_upscale_models`, `animatediff_models`, `animatediff_motion_lora`, `upscale_models`.

## Environment Knobs

Set in `.env`:
- `HF_TOKEN`: optional token for gated Hugging Face model access.
- `COMFYUI_VERSION`: ComfyUI git ref to build (default: `master`).
- `VRAM`: `auto|high|normal|low|no`.
- `INSTALL_CUSTOM_NODES`: `1|0`.
- `CUSTOM_NODES_UPDATE`: `1|0` (pull node repos on startup).
- `CUSTOM_NODES_INSTALL_DEPS`: `1|0`.

## Update Flow

Rebuild image:

```bash
bundle pods build ai/comfyui
bundle pods run ai/comfyui
```

Update custom nodes only:
1. Set `CUSTOM_NODES_UPDATE=1` in `.env`.
2. Restart with `bundle pods run ai/comfyui`.
3. Optionally set `CUSTOM_NODES_UPDATE=0` again.
