# bundle.perf_report

Extract Tracy profiler zone statistics from CSV exports, store them as structured HDF5 datasets keyed by version and platform, and generate PDF performance reports with automatic cross-version comparison.

## Public API

| Class | Module | Description |
|---|---|---|
| `ProfileExtractor` | `extractor.py` | Parse Tracy CSV files (or `.tracy` capture files) into structured `ProfileData` objects. |
| `ProfileRecord` | `extractor.py` | Single zone record (name, src_file, src_line, total_ns, total_perc, counts, mean_ns, min_ns, max_ns, std_ns). |
| `ProfileData` | `extractor.py` | All records from one CSV, with `name` and `total_calls` properties. |
| `ProfileStorage` | `storage.py` | Multi-version, multi-platform HDF5 storage via `bundle.hdf5.Store`. |

## Full pipeline

The recommended way to run profiling is through the test CLI:

```sh
bundle testing python pytest --perf
# or with a custom output directory:
bundle testing python pytest --perf --perf-output ./my-perf-dir
```

This runs the full pipeline automatically:
1. Starts `tracy-capture` in the background → `bundle.<version>.tracy`
2. Runs the test suite as a subprocess with `PERF_MODE=true` (Tracy hook active, logs silenced)
3. Waits for `tracy-capture` to finish writing when the subprocess exits
4. Exports the `.tracy` file to CSV via `tracy-csvexport`
5. Loads and stores profile data in HDF5 (`profiles.h5`)
6. Generates a PDF report (`bundle.<version>.pdf`)

Output files in `<repo>/perf/` (or `--perf-output`):
- `bundle.<version>.tracy` — raw Tracy capture
- `bundle.<version>.csv` — exported zone statistics
- `bundle.<version>.pdf` — performance report
- `profiles.h5` — historical HDF5 store

Prerequisites: `bundle tracy build` (builds and installs `tracy-capture` and `tracy-csvexport`).

## CLI

The module provides a standalone `generate` command via the bundle CLI:

```sh
# Auto-detect backend from input files
bundle perf-report generate -i perf/ -o perf/

# Explicitly select backend
bundle perf-report generate --backend tracy -i perf/ -o perf/
bundle perf-report generate --backend cprofile -i references/linux/cprofile/ -o perf/

# Custom PDF filename, skip HDF5
bundle perf-report generate -i perf/ -o perf/ --pdf-name my_report.pdf --no-h5
```

This auto-detects the profiler backend from input files (`.prof` → cProfile, `.csv`/`.tracy` → Tracy), saves profiling data to HDF5, auto-detects a previous version as baseline for comparison, and generates a PDF with per-profile charts and optional delta columns.

## Usage

### Extract profiles

```python
from bundle.perf_report import ProfileExtractor
from pathlib import Path

# From a Tracy capture file (runs tracy-csvexport internally)
profile = ProfileExtractor.extract_from_tracy(Path("bundle.1.0.0.tracy"))

# From an already-exported CSV
profile = ProfileExtractor.extract(Path("bundle.1.0.0.csv"))

# All CSV/Tracy files in a directory
profiles = ProfileExtractor.extract_all(Path("perf/"))

for rec in profile.records:
    print(f"{rec.name}: mean={rec.mean_ns}ns total={rec.total_ns}ns ({rec.counts} calls)")
```

### Store to HDF5

```python
from bundle.perf_report import ProfileStorage
from pathlib import Path

# Save with version + platform key
storage = ProfileStorage.from_directory(
    prof_dir=Path("perf/"),
    h5_path=Path("perf/profiles.h5"),
    machine_id="my-machine",
    bundle_version="1.5.0",
    platform_id="linux-x86_64-CPython3.12.8",
    platform_meta={"system": "linux", "arch": "x86_64", "processor": "..."},
)

# Discover stored data
versions = storage.list_versions()            # ["1.5.0", "1.5.1"]
platforms = storage.list_platforms("1.5.0")   # ["linux-x86_64-CPython3.12.8"]

# Read back
meta = storage.load_meta("1.5.0", "linux-x86_64-CPython3.12.8")
profiles = storage.load_profiles("1.5.0", "linux-x86_64-CPython3.12.8")
```

## Tracy CSV format

`tracy-csvexport` produces a CSV with one row per profiled zone:

| Column | Type | Description |
|---|---|---|
| `name` | str | Zone / function name |
| `src_file` | str | Source file path |
| `src_line` | int | Source line number |
| `total_ns` | int | Total time in all calls (nanoseconds) |
| `total_perc` | float | Percentage of total capture time |
| `counts` | int | Number of zone invocations |
| `mean_ns` | int | Mean time per call (nanoseconds) |
| `min_ns` | int | Minimum time per call (nanoseconds) |
| `max_ns` | int | Maximum time per call (nanoseconds) |
| `std_ns` | float | Standard deviation (nanoseconds) |

## HDF5 layout

```
/<version>/<platform_id>/
  meta                          attrs: machine_id, platform_id, bundle_version, timestamp,
                                       system, arch, node, processor, python_version, ...
  profiles/<csv_name>           structured dataset (name, src_file, src_line, total_ns,
                                       total_perc, counts, mean_ns, min_ns, max_ns, std_ns)
    attrs: csv_path, total_calls
```

## Dependencies

- `bundle.hdf5` (HDF5 store)
- `bundle.latex` (PDF generation)
- `numpy`, `matplotlib`
- `click` (CLI)
- `tracy-csvexport` (external binary, installed via `bundle tracy build`)
