#!/usr/bin/env bash
# Shared script to install thebundle.
#
# Called at two stages:
#   1. Docker build time — no volume mount, installs from PyPI or does nothing
#   2. Container runtime — source mounted at BUNDLE_SOURCE, links via .pth
#
# Dev mode expects dependencies to already be installed (by the base Dockerfile).

set -euo pipefail

BUNDLE_SOURCE="${BUNDLE_SOURCE:-/opt/thebundle}"
BUNDLE_VERSION="${BUNDLE_VERSION:-latest}"
BUNDLE_EXTRAS="${BUNDLE_EXTRAS:-}"

if [[ -n "${BUNDLE_EXTRAS}" ]]; then
    EXTRAS_SUFFIX="[${BUNDLE_EXTRAS}]"
else
    EXTRAS_SUFFIX=""
fi

# ---------------------------------------------------------------------------
# Dev mode: source is mounted → link it into Python path
# ---------------------------------------------------------------------------
if [[ -f "${BUNDLE_SOURCE}/pyproject.toml" ]]; then
    SITE_PACKAGES="$(python -c 'import site; print(site.getsitepackages()[0])')"

    # Put src/ on Python path (equivalent to editable install, but instant)
    echo "${BUNDLE_SOURCE}/src" > "${SITE_PACKAGES}/thebundle-dev.pth"

    # Create console script
    BUNDLE_BIN="$(dirname "$(which python)")/bundle"
    if [[ ! -f "${BUNDLE_BIN}" ]]; then
        cat > "${BUNDLE_BIN}" << 'SCRIPT'
#!/usr/bin/env python
from bundle.cli import main
main()
SCRIPT
        chmod +x "${BUNDLE_BIN}"
    fi

    echo "thebundle linked from ${BUNDLE_SOURCE}/src (dev mode)"

# ---------------------------------------------------------------------------
# Prod mode: no source mounted → install from PyPI if needed
# ---------------------------------------------------------------------------
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
