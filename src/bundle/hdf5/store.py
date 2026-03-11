# Copyright 2024 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import h5py
import numpy as np

if TYPE_CHECKING:
    from bundle.core.data import Data

D = TypeVar("D")


class Store:
    """Simple HDF5 store for reading and writing datasets and attributes.

    Usage::

        with Store("data.h5", mode="w") as store:
            store.write_dataset("group/data", np.array([1, 2, 3]))
            store.write_attrs("group", {"version": "1.0"})

        with Store("data.h5", mode="r") as store:
            arr = store.read_dataset("group/data")
            attrs = store.read_attrs("group")
    """

    def __init__(self, path: Path | str, mode: str = "r"):
        self.path = Path(path)
        self.mode = mode
        self._file: h5py.File | None = None

    def __enter__(self) -> Store:
        self._file = h5py.File(str(self.path), self.mode)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file:
            self._file.close()
            self._file = None

    @property
    def file(self) -> h5py.File:
        if self._file is None:
            raise RuntimeError("Store not open. Use as context manager.")
        return self._file

    def write_dataset(self, name: str, data: np.ndarray, **kwargs):
        """Write or overwrite a dataset at the given path."""
        if name in self.file:
            del self.file[name]
        self.file.create_dataset(name, data=data, **kwargs)

    def read_dataset(self, name: str) -> np.ndarray:
        """Read a dataset and return as numpy array."""
        return self.file[name][()]

    def write_attrs(self, path: str, attrs: dict | Data):
        """Write attributes to a group or dataset (creating a group if path doesn't exist).

        Accepts a plain dict or a ``bundle.core.data.Data`` instance (uses ``model_dump()``).
        Only scalar and string values are stored; complex nested objects are JSON-serialised.
        """
        from bundle.core.data import Data as DataModel

        if isinstance(attrs, DataModel):
            attrs = attrs.model_dump()
        if path in self.file:
            obj = self.file[path]
        else:
            obj = self.file.require_group(path)
        for key, value in attrs.items():
            if isinstance(value, (str, int, float, bool, np.generic)):
                obj.attrs[key] = value
            else:
                import json

                obj.attrs[key] = json.dumps(value, default=str)

    def read_attrs(self, path: str) -> dict:
        """Read all attributes from a group or dataset."""
        return dict(self.file[path].attrs)

    def read_attrs_as(self, path: str, model: type[D]) -> D:
        """Read attributes and construct a ``Data`` (or any Pydantic model) instance.

        Values that were JSON-serialised on write are automatically deserialised.
        """
        import json

        raw = self.read_attrs(path)
        parsed = {}
        for key, value in raw.items():
            if isinstance(value, (bytes, np.bytes_)):
                value = value.decode("utf-8")
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass
            parsed[key] = value
        return model(**parsed)

    def list_datasets(self, group_path: str = "/") -> list[str]:
        """List all dataset names under a group."""
        names = []

        def _visitor(name, obj):
            if isinstance(obj, h5py.Dataset):
                names.append(name)

        self.file[group_path].visititems(_visitor)
        return names

    def list_groups(self, group_path: str = "/") -> list[str]:
        """List all group names under a group."""
        names = []

        def _visitor(name, obj):
            if isinstance(obj, h5py.Group):
                names.append(name)

        self.file[group_path].visititems(_visitor)
        return names

    def has(self, name: str) -> bool:
        """Check if a dataset or group exists."""
        return name in self.file
