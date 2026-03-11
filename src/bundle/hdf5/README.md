# bundle.hdf5

Thin wrapper around `h5py` for structured HDF5 file access.

## Public API

| Class | Module | Description |
|---|---|---|
| `Store` | `store.py` | Context-managed HDF5 file handle with helpers for datasets, attributes, and groups. |

## Usage

```python
from bundle.hdf5 import Store
import numpy as np

# Write
with Store("data.h5", mode="w") as store:
    store.write_dataset("experiment/values", np.array([1.0, 2.0, 3.0]))
    store.write_attrs("experiment", {"version": "1.0", "machine": "host-abc"})

# Read
with Store("data.h5", mode="r") as store:
    arr = store.read_dataset("experiment/values")   # np.ndarray
    meta = store.read_attrs("experiment")            # dict
    names = store.list_datasets("experiment")        # ["values"]
    store.has("experiment/values")                   # True
```

## Store methods

| Method | Description |
|---|---|
| `write_dataset(name, data, **kwargs)` | Write or overwrite a dataset. |
| `read_dataset(name)` | Read a dataset as `np.ndarray`. |
| `write_attrs(path, attrs)` | Write dict of attributes to a group or dataset. |
| `read_attrs(path)` | Read all attributes as dict. |
| `list_datasets(group)` | List dataset names under a group. |
| `list_groups(group)` | List sub-group names under a group. |
| `has(name)` | Check if a dataset or group exists. |

## Dependencies

- `h5py`
- `numpy`
