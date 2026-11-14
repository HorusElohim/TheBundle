#!/usr/bin/env bash

set -euo pipefail

PPISP_SOURCE="${PPISP_SOURCE:-/opt/ppisp-src}"
PPISP_INSTALL_MODE="${PPISP_INSTALL_MODE:-editable}"
BUNDLE_SOURCE="${BUNDLE_SOURCE:-/opt/thebundle}"
INSTALL_BUNDLE="${INSTALL_BUNDLE:-1}"

if [[ ! -f "${PPISP_SOURCE}/setup.py" ]]; then
    echo "PPISP source not found at ${PPISP_SOURCE} (expected setup.py)." >&2
    echo "Mount tmp/ppisp to ${PPISP_SOURCE} before starting this pod." >&2
    exit 1
fi

INSTALL_TARGET="${PPISP_SOURCE}"
if [[ "${PPISP_INSTALL_MODE}" == "editable" ]]; then
    INSTALL_FLAGS="-e"
else
    INSTALL_FLAGS=""
fi

echo "Installing PPISP from ${INSTALL_TARGET} (mode=${PPISP_INSTALL_MODE})"
if [[ -n "${TORCH_CUDA_ARCH_LIST:-}" ]]; then
    echo "Using TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
fi

if [[ -n "${INSTALL_FLAGS}" ]]; then
    pip install ${INSTALL_FLAGS} "${INSTALL_TARGET}" --no-build-isolation
else
    pip install "${INSTALL_TARGET}" --no-build-isolation
fi

# Use shared install_bundle.sh from base image
install_bundle.sh

python -c "import torch; import ppisp; print('torch', torch.__version__, 'cuda', torch.version.cuda, 'available', torch.cuda.is_available()); print('ppisp ok', hasattr(ppisp, 'PPISP'))"

exec "$@"
