#!/usr/bin/env bash

set -euo pipefail

echo "=== Faster-GS Gaussian Training Pod ==="
python -c "
import torch
print(f'torch {torch.__version__} cuda {torch.version.cuda} available {torch.cuda.is_available()}')
try:
    import fastergs
    print('fastergs loaded successfully')
except ImportError as e:
    print(f'fastergs import warning: {e}')
"

exec "$@"
