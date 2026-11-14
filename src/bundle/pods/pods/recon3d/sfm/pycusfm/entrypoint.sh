#!/usr/bin/env bash

set -euo pipefail

PYCUSFM_DIR="${PYCUSFM_DIR:-/opt/pycusfm}"

# Install pyCuSFM if not already installed
if ! python -c "import pycusfm" >/dev/null 2>&1; then
    echo "Installing pyCuSFM from ${PYCUSFM_DIR}..."
    cd "${PYCUSFM_DIR}"
    ./install_in_host.sh
    export PATH="$HOME/.local/bin:$PATH"
fi

install_bundle.sh

echo "=== pyCuSFM Pod ==="
python -c "
import torch
print(f'torch {torch.__version__} cuda {torch.version.cuda} available {torch.cuda.is_available()}')
"
echo "pyCuSFM ready."

exec "$@"
