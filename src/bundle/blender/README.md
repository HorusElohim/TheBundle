# bundle.blender

Manage Blender installations and run headless Blender scripts from TheBundle.

## Package Layout

```
src/bundle/blender/
├── README.md               # This file
├── __init__.py
├── cli.py                  # `bundle blender` subcommands
├── app/
│   ├── __init__.py
│   └── manager.py          # BlenderAppManager — download and install releases
├── runtime/
│   ├── __init__.py
│   ├── app.py              # BlenderRuntime — discover Blender environments
│   └── session.py          # BlenderSession — launch Blender as a subprocess
└── scripts/
    └── audio/
        └── generate.py     # Blender-embedded script: audio-driven geometry nodes
```

## Guiding Principles

- Separate host orchestration code (runs with CPython) from in-Blender code (executed by `bpy`).
- Model every configurable knob with `bundle.core.data.Data` for validation and JSON round-trips.
- Route all telemetry through `bundle.core.logger` and `bundle.core.tracer`.
- Treat Blender scenes as build artifacts: stage inputs, run deterministic pipelines, emit `.blend`, renders, or glTF outputs.

## Core Abstractions

**BlenderEnvironment** (`runtime/`)
Describes a discovered Blender installation: executable path, bundled Python, and scripts directory.

**BlenderAppManager** (`app/manager.py`)
Downloads and installs Blender releases into a user-space directory. Respects `BUNDLE_BLENDER_HOME` and `BUNDLE_BLENDER_CACHE` environment variable overrides.

**BlenderRuntime** (`runtime/app.py`)
Discovers Blender installations via managed installs, environment variables (`BUNDLE_BLENDER_EXECUTABLE`, `BUNDLE_BLENDER_PYTHON`, `BUNDLE_BLENDER_ROOT`), platform candidates, and `PATH`.

**BlenderSession** (`runtime/session.py`)
Wraps `bundle.core.process.Process` to launch Blender headless (`--background --python <script>`).

## CLI Quickstart

```bash
# Auto-discover installed Blender and print paths
bundle blender info

# Download a managed Blender release
bundle blender download --version 4.5.0

# Install TheBundle into Blender's bundled Python
bundle blender install
```

## Environment Variable Overrides

| Variable | Purpose |
|---|---|
| `BUNDLE_BLENDER_EXECUTABLE` | Path to the `blender` binary |
| `BUNDLE_BLENDER_PYTHON` | Path to Blender's bundled Python interpreter |
| `BUNDLE_BLENDER_ROOT` | Root of a Blender installation directory |
| `BUNDLE_BLENDER_HOME` | Override managed install root |
| `BUNDLE_BLENDER_CACHE` | Override download cache root |

## User-space Install Root

- **macOS**: `~/Library/Application Support/TheBundle/blender`
- **Linux**: `${XDG_DATA_HOME:-~/.local/share}/thebundle/blender`
- **Windows**: `%LOCALAPPDATA%/TheBundle/blender`

Cached archives use the matching cache root and are reused across installs. Discovery always checks the managed install location before system installs.
