# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import argparse
import asyncio
import zipfile
from pathlib import Path

import torch
import torch.nn.functional as F
from ppisp import PPISP
from torchvision.io import read_image
from torchvision.utils import save_image
from tqdm.auto import tqdm

from bundle import core

URL = "http://storage.googleapis.com/gresearch/refraw360/360_v2.zip"
log = core.logger.setup_root_logger(name="ppisp.dataset", level=core.logger.Level.INFO)


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="PPISP + Mip-NeRF 360 smoke test")
    p.add_argument("--data-dir", default="/workspace/data")
    p.add_argument(
        "--images-dir",
        default="",
        help="Direct image folder (overrides --scene download/layout)",
    )
    p.add_argument("--save-dir", default="/workspace/results")
    p.add_argument("--scene", default="garden")
    p.add_argument("--image-size", type=int, default=256)
    p.add_argument("--samples", type=int, default=64)
    p.add_argument("--steps", type=int, default=25)
    p.add_argument("--log-every", type=int, default=5)
    return p.parse_args()


async def download(url: str, dst: Path) -> None:
    if dst.exists():
        return
    ok = await core.DownloaderTQDM(url=url, destination=dst).download()
    assert ok, f"Failed download: {url}"


def ensure_data(root: Path, scene: str) -> list[Path]:
    root.mkdir(parents=True, exist_ok=True)
    z = root / "360_v2.zip"
    ds = root / "360_v2"
    if not ds.exists():
        asyncio.run(download(URL, z))
        with zipfile.ZipFile(z, "r") as fh:
            fh.extractall(root)
    scene_root = ds / scene
    for name in ("images_4", "images_2", "images"):
        p = scene_root / name
        files = sorted([*p.glob("*.png"), *p.glob("*.jpg"), *p.glob("*.jpeg")])
        if files:
            return files
    avail = ", ".join(sorted(p.name for p in ds.iterdir() if p.is_dir()))
    raise FileNotFoundError(f"scene '{scene}' not found or empty. available: {avail}")


def images_in(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    patterns = ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG")
    files = sorted({p for pat in patterns for p in folder.rglob(pat)})
    if not files:
        hints = ", ".join(sorted(p.name for p in folder.iterdir() if p.is_dir())[:8])
        hint_msg = f" Subfolders: {hints}" if hints else ""
        raise FileNotFoundError(f"No images found in {folder}.{hint_msg}")
    return files


def load(paths: list[Path], size: int) -> list[torch.Tensor]:
    out: list[torch.Tensor] = []
    for p in paths:
        x = read_image(str(p)).float().div(255)
        x = x[:3] if x.shape[0] > 3 else x.repeat(3, 1, 1) if x.shape[0] == 1 else x
        x = F.interpolate(x[None], size=(size, size), mode="bilinear", align_corners=False)[0]
        out.append(x.permute(1, 2, 0).contiguous())
    return out


def novel_inputs(
    images: list[torch.Tensor],
) -> tuple[dict[str, torch.Tensor], dict[str, int]]:
    n = len(images)
    c = n // 2
    q = max(1, n // 4)
    ids = {
        "center": c % n,
        "north": (c - q) % n,
        "south": (c + q) % n,
        "east": (c + 2 * q) % n,
        "west": (c - 2 * q) % n,
    }
    return {k: images[i] for k, i in ids.items()}, ids


def main() -> None:
    a = args()
    assert torch.cuda.is_available(), "CUDA is required."
    custom_images = Path(a.images_dir) if a.images_dir else None
    files = images_in(custom_images) if custom_images else ensure_data(Path(a.data_dir), a.scene)
    n = min(max(1, a.samples), len(files))
    idx = torch.linspace(0, len(files) - 1, n).round().long().tolist()
    imgs = load([files[i] for i in idx], a.image_size)
    h, w, _ = imgs[0].shape
    d = torch.device("cuda")
    xy = torch.stack(
        torch.meshgrid(torch.arange(h, device=d), torch.arange(w, device=d), indexing="ij")[::-1],
        -1,
    ).float()
    m = PPISP(num_cameras=1, num_frames=n).to(d).train()
    opts = m.create_optimizers()
    sch = m.create_schedulers(opts, max(1, a.steps))

    bar = tqdm(range(a.steps), desc="ppisp-train", unit="step")
    for s in bar:
        f = s % n
        x = imgs[f].to(d)
        y = m(x, xy, (w, h), 0, f)
        loss = (y - x).square().mean() + m.get_regularization_loss()
        loss.backward()
        for o in opts:
            o.step()
            o.zero_grad(set_to_none=True)
        for lr in sch:
            lr.step()
        if s % max(1, a.log_every) == 0 or s == a.steps - 1:
            log.info("step=%03d frame=%03d loss=%.6f", s, f, float(loss.item()))
            bar.set_postfix(loss=f"{float(loss.item()):.6f}", frame=f)

    m.eval()
    x0 = imgs[0].to(d)
    with torch.no_grad():
        y0 = m(x0, xy, (w, h), 0, 0)
        seeds, ids = novel_inputs(imgs)
        novels = {name: m(v.to(d), xy, (w, h), 0, -1) for name, v in seeds.items()}
    save = Path(a.save_dir)
    save.mkdir(parents=True, exist_ok=True)
    save_image(
        torch.cat([x0, y0, (y0 - x0).abs()], 1).permute(2, 0, 1).cpu().clamp(0, 1),
        save / "frame0_input_output_diff.png",
    )
    save_image(x0.permute(2, 0, 1).cpu().clamp(0, 1), save / "frame0_input.png")
    save_image(y0.permute(2, 0, 1).cpu().clamp(0, 1), save / "frame0_output.png")
    for name, img in novels.items():
        save_image(img.permute(2, 0, 1).cpu().clamp(0, 1), save / f"novel_view_{name}.png")
    novel_panel = torch.cat([novels[k] for k in ("center", "north", "south", "east", "west")], 1)
    save_image(novel_panel.permute(2, 0, 1).cpu().clamp(0, 1), save / "novel_views_panel.png")
    scene_name = custom_images.name if custom_images else a.scene
    (save / "scene.txt").write_text(scene_name, encoding="utf-8")
    (save / "novel_views.txt").write_text("center\nnorth\nsouth\neast\nwest\n", encoding="utf-8")
    (save / "novel_view_sources.txt").write_text(
        "\n".join([f"{k}:{v}" for k, v in ids.items()]) + "\n",
        encoding="utf-8",
    )
    log.info("done scene=%s samples=%d steps=%d saved=%s", scene_name, n, a.steps, save)


if __name__ == "__main__":
    main()
