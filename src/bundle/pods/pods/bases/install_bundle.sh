#!/usr/bin/env bash
# Shared script to install thebundle — called by pod entrypoints.
#
# Dev mode:  mount local repo at BUNDLE_SOURCE → editable install
# Prod mode: no mount → install from PyPI
#
# Usage: source install_bundle.sh   (or call directly)

set -euo pipefail

BUNDLE_SOURCE="${BUNDLE_SOURCE:-/opt/thebundle}"
BUNDLE_VERSION="${BUNDLE_VERSION:-latest}"
BUNDLE_EXTRAS="${BUNDLE_EXTRAS:-}"

# Build the extras suffix: ".[web,report]" or just "."
if [[ -n "${BUNDLE_EXTRAS}" ]]; then
    EXTRAS_SUFFIX="[${BUNDLE_EXTRAS}]"
else
    EXTRAS_SUFFIX=""
fi

if [[ -f "${BUNDLE_SOURCE}/pyproject.toml" ]]; then
    echo "Installing thebundle from local source: ${BUNDLE_SOURCE} (editable)"
    pip install -e "${BUNDLE_SOURCE}${EXTRAS_SUFFIX}" --no-build-isolation -q
else
    if python -c "import bundle" >/dev/null 2>&1; then
        echo "thebundle already installed: $(python -c 'import bundle; print(bundle.__version__)' 2>/dev/null || echo 'unknown')"
    else
        echo "Installing thebundle from PyPI (version=${BUNDLE_VERSION})"
        if [[ "${BUNDLE_VERSION}" == "latest" ]]; then
            pip install "thebundle${EXTRAS_SUFFIX}" -q
        else
            pip install "thebundle==${BUNDLE_VERSION}${EXTRAS_SUFFIX}" -q
        fi
    fi
fi
