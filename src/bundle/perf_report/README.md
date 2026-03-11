# bundle.perf_report

Extract cProfile `.prof` files, store them as structured HDF5 datasets keyed by version and platform, and generate PDF performance reports with automatic cross-version comparison.

## Public API

| Class | Module | Description |
|---|---|---|
| `ProfileExtractor` | `extractor.py` | Parse `.prof` files into structured `ProfileData` objects. |
| `ProfileRecord` | `extractor.py` | Single function record (file, line, function, calls, total time, cumulative time). |
| `ProfileData` | `extractor.py` | All records from one `.prof` file, with `name` and `total_calls` properties. |
| `ProfileStorage` | `storage.py` | Multi-version, multi-platform HDF5 storage via `bundle.hdf5.Store`. |

## CLI

The module provides a single `report` command that:
1. Extracts `.prof` files from the input directory
2. Saves profiling data and platform metadata to HDF5
3. Auto-detects a previous version in the HDF5 as baseline for comparison
4. Generates a PDF with a platform info table, per-profile charts, and optional delta columns

```sh
python -m bundle.perf_report.report --input-path references/ --output-dir performances/
```

Output: `perf_report_<version>_<platform_id>.pdf` + `profiles.h5`

Use `PERF_MODE=1` when running tests to silence rich logging overhead during profiling.

## Usage

### Extract profiles

```python
from bundle.perf_report import ProfileExtractor

# Single file
profile = ProfileExtractor.extract(Path("test_foo.prof"))
for rec in profile.records:
    print(f"{rec.function}: {rec.cumulative_time:.6f}s ({rec.call_count} calls)")

# All .prof files in a directory tree
profiles = ProfileExtractor.extract_all(Path("references/windows/cprofile/"))
```

### Store to HDF5

```python
from bundle.perf_report import ProfileStorage

# Save with version + platform key
storage = ProfileStorage.from_directory(
    prof_dir=Path("references/"),
    h5_path=Path("profiles.h5"),
    machine_id="my-machine",
    bundle_version="1.5.0",
    platform_id="linux-x86_64-CPython3.12.8",
    platform_meta={"system": "linux", "arch": "x86_64", "processor": "..."},
)

# Discover stored data
versions = storage.list_versions()          # ["1.5.0", "1.5.1"]
platforms = storage.list_platforms("1.5.0")  # ["linux-x86_64-CPython3.12.8"]

# Read back
meta = storage.load_meta("1.5.0", "linux-x86_64-CPython3.12.8")
profiles = storage.load_profiles("1.5.0", "linux-x86_64-CPython3.12.8")
```

## HDF5 layout

```
/<version>/<platform_id>/
  meta                         attrs: machine_id, platform_id, bundle_version, timestamp,
                                      system, arch, node, processor, python_version, ...
  profiles/<prof_name>         structured dataset (file, line_number, function, call_count,
                                      total_time, cumulative_time)
    attrs: prof_path, total_calls
```

## Dependencies

- `bundle.hdf5` (HDF5 store)
- `bundle.latex` (PDF generation)
- `numpy`, `matplotlib`
- `click` (CLI)
- Python `pstats` (stdlib)
