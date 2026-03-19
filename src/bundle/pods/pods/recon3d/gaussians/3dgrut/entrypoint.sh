#!/usr/bin/env bash

set -euo pipefail

install_bundle.sh

echo "=== 3DGRUT Gaussian Training Pod ==="
python -c "
import torch
print(f'torch {torch.__version__} cuda {torch.version.cuda} available {torch.cuda.is_available()}')
try:
    import threedgrut
    print('3dgrut loaded successfully')
except ImportError as e:
    print(f'3dgrut import warning: {e}')
"

exec "$@"
