# bundle.perf_report

Extract cProfile `.prof` files and store them as structured HDF5 datasets, tagged with machine ID and bundle version for cross-run comparisons.

## Public API

| Class | Module | Description |
|---|---|---|
| `ProfileExtractor` | `extractor.py` | Parse `.prof` files into structured `ProfileData` objects. |
| `ProfileRecord` | `extractor.py` | Single function record (file, line, function, calls, total time, cumulative time). |
| `ProfileData` | `extractor.py` | All records from one `.prof` file, with `name` and `total_calls` properties. |
| `ProfileStorage` | `storage.py` | Save/load profile data to HDF5 via `bundle.hdf5.Store`. |

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

# Save (writes machine_id + version as metadata)
storage = ProfileStorage.from_directory(
    prof_dir=Path("references/"),
    h5_path=Path("profiles.h5"),
    machine_id="my-machine",
    bundle_version="1.5.0",
)

# Read back
meta = storage.load_meta()          # {"machine_id": ..., "bundle_version": ..., "timestamp": ...}
names = storage.load_profile_names() # ["test_foo", "test_bar", ...]
data = storage.load_profile("test_foo")  # np.ndarray (structured)
```

## HDF5 layout

```
/meta                          attrs: machine_id, bundle_version, timestamp
/profiles/<prof_name>          structured dataset (file, line_number, function, call_count, total_time, cumulative_time)
  attrs: prof_path, total_calls
```

## Dependencies

- `bundle.hdf5` (HDF5 store)
- `numpy`
- Python `pstats` (stdlib)
