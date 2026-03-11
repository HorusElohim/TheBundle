# bundle.hdf5

Thin wrapper around `h5py` for structured HDF5 file access, with native support for `bundle.core.data.Data` (Pydantic) models.

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

### Data model support

`write_attrs` accepts `dict` or `bundle.core.data.Data` instances (uses `model_dump()`). Complex nested values are JSON-serialized automatically.

`read_attrs_as` reconstructs a Pydantic model from stored attributes:

```python
from bundle.core.data import Data
from bundle.hdf5 import Store

class RunMeta(Data):
    version: str
    machine: str

with Store("data.h5", mode="w") as store:
    store.write_attrs("run", RunMeta(version="1.0", machine="host"))

with Store("data.h5", mode="r") as store:
    meta = store.read_attrs_as("run", RunMeta)  # RunMeta(version='1.0', machine='host')
```

## Store methods

| Method | Description |
|---|---|
| `write_dataset(name, data, **kwargs)` | Write or overwrite a dataset. |
| `read_dataset(name)` | Read a dataset as `np.ndarray`. |
| `write_attrs(path, attrs)` | Write `dict` or `Data` instance as HDF5 attributes. |
| `read_attrs(path)` | Read all attributes as `dict`. |
| `read_attrs_as(path, model)` | Read attributes and reconstruct as a `Data` model. |
| `list_datasets(group)` | List dataset names under a group. |
| `list_groups(group)` | List sub-group names under a group. |
| `has(name)` | Check if a dataset or group exists. |

## Dependencies

- `h5py`
- `numpy`
