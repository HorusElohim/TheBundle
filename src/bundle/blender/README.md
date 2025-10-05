# bundle.blender Manifest

## Vision
- Provide a reusable backbone for any Blender project shipped with TheBundle while remaining lean and composable.
- Standardize configuration, logging, tracing, and asset access by leaning on `bundle.core` primitives.
- Keep host side Python minimal yet powerful so teams can assemble new pipelines by combining reusable building blocks.

## Guiding Principles
- Separate host orchestration code (runs with CPython) from in-Blender code (executed by `bpy`).
- Model every configurable knob with `bundle.core.data.Data` to gain validation, JSON round-trips, and schema exports.
- Route all telemetry through `bundle.core.logger` and `bundle.core.tracer` to stay consistent with the rest of the bundle CLI.
- Prefer composable services (sessions, asset managers, registries) over monolithic scripts so new projects can opt in selectively.
- Treat Blender scenes as build artifacts: stage inputs, run deterministic pipelines, emit `.blend`, renders, or glTF outputs.

## High Level Architecture

```
+-----------------------------+      +-----------------------------+
| bundle.blender.cli          |----->| bundle.blender.runtime      |
|  - argparse entrypoints     |      |  - BlenderLauncher          |
|  - shared CLI options       |      |  - Session and Environment  |
+-------------^---------------+      |  - Package assembler        |
              |                      +-------------^---------------+
              |                                    |
+-------------+---------------+      +-------------+----------------+
| bundle.blender.projects     |<---->| bundle.blender.toolkit       |
|  - Project registry         |      |  - Geometry foundations      |
|  - Project definitions      |      |  - Material and shading      |
|  - Pipelines (host tasks)   |      |  - Adapters and animation    |
+-----------------------------+      +------------------------------+
```

Host Python prepares configs, assets, and environment variables, launches Blender in background, then hands control to a script module imported inside Blender. Communication stays file based (JSON configs, temporary directories) for robustness.

## Proposed Package Layout

```
src/bundle/blender/
|-- README.md               # This manifest
|-- __init__.py
|-- cli.py                  # `bundle blender ...` subcommands
|-- runtime/
|   |-- __init__.py
|   |-- env.py              # Paths, temp dirs, bundle root helpers
|   |-- session.py          # Launch or find Blender, execute commands
|   `-- packaging.py        # Pack config and toolkit bundles for subprocess
|-- config/
|   |-- __init__.py
|   `-- base.py             # Shared Data models (GlobalConfig, Paths)
|-- projects/
|   |-- __init__.py
|   |-- base.py             # Abstract Project and Pipeline interfaces
|   |-- registry.py         # Discoverable project registry
|   `-- audio_grid/
|       |-- __init__.py
|       |-- config.py       # AudioGridConfig(Data)
|       |-- pipeline.py     # Host side preparation (audio analysis)
|       `-- script.py       # Entry executed inside Blender
|-- toolkit/
|   |-- __init__.py
|   |-- adapters/
|   |   |-- __init__.py
|   |   `-- context.py      # Logging bootstrap, scene/session guards
|   |-- geometry/
|   |   |-- __init__.py
|   |   |-- primitives.py   # Mesh factories, grid builders, helpers
|   |   `-- nodes.py        # Geometry node graphs and modifiers
|   |-- materials/
|   |   |-- __init__.py
|   |   |-- library.py      # Shared shader node stacks
|   |   `-- drivers.py      # Material driver wiring helpers
|   |-- animation/
|   |   |-- __init__.py
|   |   `-- drivers.py      # Timeline baking, procedural drivers
|   `-- io/
|       |-- __init__.py
|       `-- assets.py       # Asset loading, link/append utilities
`-- assets/
    `-- README.md           # Asset import policy and git-lfs notes
```

Key ideas:
- `runtime` keeps direct interaction with the Blender executable and integrates with `bundle.core.process` and `bundle.core.utils` helpers.
- `config` offers base Data classes (paths, Blender executable overrides, logging toggles) shared by all projects.
- `projects` contain thin host side orchestration. Each project exposes `HOST_PIPELINE` (callable) and declares the toolkit entry module consumed by Blender.
- `toolkit` centralizes reusable Blender-facing code. Specialised subpackages (adapters, geometry, materials, animation, io) let projects import only what they need and scale independently.
- `assets` (optional) stores generic textures, HDRIs, or geometry seeds. Project specific assets remain colocated under each project folder to keep versioning clear.

## Toolkit Modules

**adapters**
- Bridge host configuration into running Blender sessions.
- Provide context managers for logging setup, dependency injection, and scene validation.

**geometry**
- Offer primitives (`ensure_mesh`, grid/curve generators) plus higher level geometry node graphs.
- Encapsulate naming conventions so drivers and modifiers remain stable across projects.

**materials**
- Contain a shader library (procedural neon, matte, PBR bridges) and driver helpers to connect animation data to node inputs.
- Expose factories returning fully wired node groups ready for assignment in geometry pipelines.

**animation**
- Implement driver wiring, keyframe baking, and signal processing helpers (FFT, smoothing) that feed geometry and materials.
- Enable reusable “drive-by-data” patterns (audio amplitude, CSV curves, physics caches).

**io**
- Handle asset discovery, linking/appending `.blend` libraries, and exporting renders or glTF/glb packages.
- Ensure paths honor the runtime environment abstraction (`bundle.core.platform`).

## Core Abstractions

**Project**
- Defined in `projects.base.Project`. Carries metadata (name, description, tags), configuration schema, and hooks (`prepare()`, `render()`, `package_artifacts()`).
- Registers itself through `projects.registry.register(Project)`. Discovery powers `bundle blender list` and `bundle blender run <project>` CLI flows.

**Pipeline**
- Composed of async steps that reuse `bundle.core.tracer.Async.decorator.call_raise` for observability.
- Steps interact with `runtime.Session` for launching Blender, pushing scripts, collecting outputs.

**BlenderSession**
- Wraps `bundle.core.process.run_process` to start Blender with `--background --python path/to/entrypoint.py`.
- Injects config JSON path via environment variables (for example `BUNDLE_BLENDER_CONFIG`) and flips logging verbosity with `bundle.core.logger.setup_root_logger` inside the script.

**Script Packages**
- Each project exports a `script.py` providing `main()` that Blender executes. It reads config using `bundle.core.data.Data.from_json`, pulls building blocks from `toolkit`, and saves the `.blend` file plus optional renders.
- Shared helpers (geometry node builders, driver wiring, shader setup) live under `toolkit/` so new projects only assemble them, not re-implement them.

**Configuration**
- Base class provides `BlenderPaths` (executable, scripts_dir, temp_dir) and `RenderSettings` (engine, resolution, format).
- Project configs extend the base to add custom fields (for example audio normalization parameters). JSON schemas surface via CLI (`bundle blender schema <project>`).

**CLI Integration**
- `bundle blender list` - enumerate registered projects.
- `bundle blender run <project> [--config path.json] [--output dir]` - run the pipeline end to end.
- `bundle blender bake <project>` - run host side preparation only and produce a config package for manual use inside Blender.
- Reuse shared CLI utilities from `bundle.cli` (logging flags, `--no-logs`, `--no-cprof`).

## Workflow Overview

1. User invokes CLI (for example `bundle blender run audio_grid`).
2. CLI loads `audio_grid.config.AudioGridConfig` using default values or provided JSON, validated by `bundle.core.data`.
3. `Project.prepare()` performs CPU friendly preparation (audio FFTs, reference snapshots) using `numpy` or other host libraries. Outputs land in a temp workspace (prefer `bundle.core.utils.ensure_dir`).
4. `runtime.Session.run_script()` launches Blender, points to `projects/audio_grid/script.py`, and passes staged assets plus the config path.
5. Inside Blender, `script.main()` configures logging, loads config, constructs geometry and materials via the toolkit, wires drivers, triggers renders, and saves outputs.
6. Host pipeline collects artifacts (blend file, image sequences, logs). Optional packaging step copies them into `references/...` or a user supplied output directory.

## Testing Strategy
- Host side units: pure Python pieces (config validation, registry, session invocation args) tested under `tests/blender/...` with standard `pytest`.
- Toolkit units: run `pytest` with mock `bpy` shims to cover geometry/material factory contracts without requiring Blender.
- Integration: mark tests that require Blender with `pytest.mark.blender` and guard via environment flags so CI can skip unless Blender is available.
- Golden references: if renders are deterministic, place baseline artifacts under `references/<platform>/ref/blender/<project>` and keep `failed` empty per repo policy.
- CLI smoke tests: exercise `bundle blender list` and configuration schema commands without launching Blender.

## Migration Notes for `scripts/audio/generate.py`
- Split host and script logic: FFT preparation remains host side; geometry, drivers, and material creation move into `projects/audio_grid/script.py` using toolkit helpers.
- Extract reusable utilities (for example `ensure_target_mesh`, `build_neon_shader`) into `toolkit.geometry` and `toolkit.materials` modules.
- Replace the global config loader with `AudioGridConfig` in `projects.audio_grid.config`. Default paths live beside project assets instead of hard coded absolute paths.

## Immediate Next Steps
1. Scaffold the package skeleton (empty modules per structure above) plus a minimal CLI that prints the registry.
2. Port `AudioDriverConfig` into `projects.audio_grid.config` and make the script consume staged JSON via the adapter layer.
3. Build `runtime.Session` capable of launching Blender in background; start with a dry run that only echoes the command when Blender is missing.
4. Flesh out `toolkit.geometry` and `toolkit.materials` by migrating reusable pieces from the current audio script.
5. Write host level tests for the registry, config serialization, and toolkit factories (with `bpy` mocks) before expanding to additional projects.

This manifest should stay close to reality as the package evolves. Revisit after the first two projects land to confirm abstractions remain lean and scalable.
