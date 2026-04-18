#!/usr/bin/env python3
"""Thin wrapper around NeRFICG + Faster-GS training.

Mirrors the CLI shape of 3dgrut's ``train.py`` so the host-side
``GaussiansStage`` can invoke it uniformly::

    python /opt/train_fastergs.py \\
        --path /workspace/data/bicycle \\
        --out-dir /workspace/data/bicycle/runs \\
        --experiment default

The NeRFICG native flow is:
    1. ``scripts/create_config.py`` emits a YAML template.
    2. Edit ``GLOBAL.DATASET_TYPE``, ``DATASET.PATH``, ``TRAINING.OUTPUT_DIR``.
    3. ``scripts/train.py -c <config>.yaml`` runs the training loop.

This wrapper automates steps 1–3 so the stage stays as a single subprocess call.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

NERFICG_DIR = Path(os.environ.get("NERFICG_DIR", "/opt/nerficg"))


def _patch_config(config_path: Path, dataset_path: Path, out_dir: Path) -> None:
    """Rewrite dataset path + output directory in an auto-generated config."""
    text = config_path.read_text()
    patched: list[str] = []
    for line in text.splitlines():
        if "DATASET_TYPE" in line:
            patched.append("GLOBAL.DATASET_TYPE: Colmap")
        elif line.lstrip().startswith("PATH:"):
            patched.append(f"  PATH: {dataset_path}")
        elif "OUTPUT_DIR" in line:
            patched.append(f"  OUTPUT_DIR: {out_dir}")
        else:
            patched.append(line)
    config_path.write_text("\n".join(patched) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Faster-GS training wrapper")
    parser.add_argument("--path", required=True, type=Path, help="Scene root (images/ + sparse/0/)")
    parser.add_argument("--out-dir", required=True, type=Path, help="Directory for run outputs")
    parser.add_argument("--experiment", default="default", help="Experiment name")
    parser.add_argument("--method", default="FasterGS", help="NeRFICG method name")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    configs_dir = NERFICG_DIR / "configs"
    configs_dir.mkdir(parents=True, exist_ok=True)
    config_name = f"{args.experiment}_fastergs"
    config_path = configs_dir / f"{config_name}.yaml"

    create_cmd = [
        sys.executable,
        str(NERFICG_DIR / "scripts" / "create_config.py"),
        "-m", args.method,
        "-d", "Colmap",
        "-o", config_name,
    ]
    print(f"[fastergs] creating config: {' '.join(create_cmd)}", flush=True)
    subprocess.run(create_cmd, check=True, cwd=str(NERFICG_DIR))

    if not config_path.exists():
        print(f"[fastergs] ERROR: config not found at {config_path}", file=sys.stderr)
        return 1

    _patch_config(config_path, args.path, args.out_dir / args.experiment)

    train_cmd = [
        sys.executable,
        str(NERFICG_DIR / "scripts" / "train.py"),
        "-c", f"configs/{config_name}.yaml",
    ]
    print(f"[fastergs] training: {' '.join(train_cmd)}", flush=True)
    result = subprocess.run(train_cmd, cwd=str(NERFICG_DIR))
    if result.returncode != 0:
        return result.returncode

    # NeRFICG writes checkpoints + renders under OUTPUT_DIR. Surface a model.ply
    # at the top of the experiment dir so downstream stages (Blender, USD)
    # don't need to grep subfolders.
    exp_dir = args.out_dir / args.experiment
    for candidate in exp_dir.rglob("*.ply"):
        target = exp_dir / "model.ply"
        if not target.exists() and candidate != target:
            shutil.copy2(candidate, target)
            print(f"[fastergs] surfaced {candidate} -> {target}", flush=True)
        break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
