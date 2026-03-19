#!/usr/bin/env bash

set -euo pipefail

install_bundle.sh

echo "=== COLMAP SfM Pod ==="
which colmap >/dev/null 2>&1 || { echo "COLMAP not found" >&2; exit 1; }
echo "CUDA: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'no GPU detected')"

exec "$@"
