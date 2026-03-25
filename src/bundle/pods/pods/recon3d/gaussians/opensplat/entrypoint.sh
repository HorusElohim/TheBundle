#!/usr/bin/env bash

set -euo pipefail

install_bundle.sh

echo "=== OpenSplat Gaussians Pod ==="
which opensplat >/dev/null 2>&1 || { echo "OpenSplat not found" >&2; exit 1; }

exec "$@"
