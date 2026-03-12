# bundle.tracy

Tracy profiler integration for TheBundle. Provides nanosecond-resolution, real-time profiling of Python code via a pybind11 C++ extension wrapping [Tracy v0.13.1](https://github.com/wolfpld/tracy).

When the `_tracy_ext` native extension is built and a Tracy viewer/capture is connected, all instrumented calls are live-profiled across all threads. When the extension is absent, every call is a silent no-op — zero overhead, no code changes needed.

## Quick start

### Build

```sh
# Build the Python extension + tracy-capture + tracy-csvexport
bundle tracy build

# Build individual components
bundle tracy build extension       # Python pybind11 extension only
bundle tracy build capture         # tracy-capture CLI tool
bundle tracy build csvexport       # tracy-csvexport CLI tool
bundle tracy build profiler        # Tracy viewer GUI (needs GLFW, freetype, capstone)
```

### Usage

#### Manual zones

```python
from bundle import tracy

# Context manager
with tracy.zone("load"):
    data = load()

# Decorator (sync or async)
@tracy.zone("process")
async def process(data): ...
```

#### Auto-instrument all Python calls

```python
import bundle.tracy as tracy

tracy.start()              # install sys.setprofile hook
run_workload()
tracy.stop()               # remove hook, flush pending data

# Filter to bundle code only (skip stdlib/third-party)
tracy.start(bundle_only=True)
```

#### Live metrics and annotations

```python
tracy.plot("queue_size", len(q))              # numeric plot in viewer
tracy.message("batch complete", color=0x00FF00)  # timeline annotation
tracy.frame_mark()                             # frame boundary marker
tracy.set_thread_name("worker-1")             # name the current thread
```

## Public API

| Function / Class | Description |
|---|---|
| `zone(name, color=0)` | Context manager and decorator for manual profiling zones |
| `start(bundle_only=False)` | Install Tracy as the global Python profiler via `sys.setprofile` |
| `stop()` | Remove the profiler hook and flush pending data |
| `frame_mark(name=None)` | Emit a frame boundary marker |
| `plot(name, value)` | Record a live numeric value as a plot |
| `message(text, color=0)` | Add a text annotation on the timeline |
| `set_thread_name(name)` | Name the calling thread in the viewer |
| `is_connected()` | True when a Tracy viewer is actively connected |
| `ENABLED` | Boolean — True when the native extension is loaded |

## Full profiling pipeline

The recommended way to run profiling is through the test CLI:

```sh
# Profile with Tracy (real-time viewing)
bundle testing python pytest --tracy

# Profile + generate PDF report
bundle testing python pytest --tracy --report

# Custom output directory
bundle testing python pytest --tracy --report --perf-output ./my-perf-dir
```

This runs the full pipeline automatically:
1. Starts `tracy-capture` in the background
2. Runs the test suite as a subprocess with `PERF_MODE=true` (Tracy hook active, logs silenced)
3. Waits for `tracy-capture` to finish writing when the subprocess exits
4. Exports the `.tracy` file to CSV via `tracy-csvexport`
5. Generates a PDF report with per-zone charts and cross-version comparison (when `--report` is used)

Prerequisites: `bundle tracy build` (builds and installs `tracy-capture` and `tracy-csvexport`).

## Architecture

```
bundle.tracy/
  __init__.py          # Python API: zone, start/stop, plot, message, etc.
  _fallback.py         # No-op stubs when native extension is unavailable
  cli.py               # `bundle tracy build` CLI commands
  pyproject.toml       # [tool.pybind11] declarative extension config
  setup.py             # Pybind.setup() entry point
  pybind_plugin.py     # PybindPluginSpec for platform-specific flags
  binding/
    _tracy_ext.cpp     # pybind11 C++ extension wrapping Tracy's C API
  vendor/
    tracy/             # Tracy v0.13.1 git submodule
```

The extension is built via `bundle.pybind` — the declarative config lives in the tracy-local `pyproject.toml` and platform-specific flags (TRACY_ENABLE, linker libs) are injected by `TracyPlatformPlugin`. The extension is **not** built during `pip install thebundle` to avoid requiring a C++20 compiler and the Tracy submodule; instead it is built on-demand via `bundle tracy build extension`.

## Dependencies

- Tracy v0.13.1 (vendored as git submodule)
- `pybind11` (build-time)
- C++20 compiler (MSVC on Windows, GCC/Clang on Linux/macOS)
- `bundle.pybind.services.cmake` (for building native tools via CLI)
