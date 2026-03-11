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

import tempfile
from pathlib import Path

import numpy as np
import pytest

from bundle.hdf5 import Store


@pytest.fixture
def tmp_h5(tmp_path):
    return tmp_path / "test.h5"


class TestStore:
    def test_write_and_read_dataset(self, tmp_h5):
        data = np.array([1.0, 2.0, 3.0])
        with Store(tmp_h5, mode="w") as store:
            store.write_dataset("my/data", data)

        with Store(tmp_h5, mode="r") as store:
            result = store.read_dataset("my/data")
            np.testing.assert_array_equal(result, data)

    def test_write_and_read_attrs(self, tmp_h5):
        with Store(tmp_h5, mode="w") as store:
            store.write_attrs("meta", {"version": "1.0", "count": 42})

        with Store(tmp_h5, mode="r") as store:
            attrs = store.read_attrs("meta")
            assert attrs["version"] == "1.0"
            assert attrs["count"] == 42

    def test_overwrite_dataset(self, tmp_h5):
        with Store(tmp_h5, mode="w") as store:
            store.write_dataset("vals", np.array([1, 2]))
            store.write_dataset("vals", np.array([10, 20, 30]))

        with Store(tmp_h5, mode="r") as store:
            result = store.read_dataset("vals")
            np.testing.assert_array_equal(result, np.array([10, 20, 30]))

    def test_list_datasets(self, tmp_h5):
        with Store(tmp_h5, mode="w") as store:
            store.write_dataset("group/a", np.array([1]))
            store.write_dataset("group/b", np.array([2]))
            store.write_dataset("other", np.array([3]))

        with Store(tmp_h5, mode="r") as store:
            all_ds = store.list_datasets()
            assert "group/a" in all_ds
            assert "group/b" in all_ds
            assert "other" in all_ds

            group_ds = store.list_datasets("group")
            assert "a" in group_ds
            assert "b" in group_ds

    def test_list_groups(self, tmp_h5):
        with Store(tmp_h5, mode="w") as store:
            store.write_dataset("g1/sub/data", np.array([1]))

        with Store(tmp_h5, mode="r") as store:
            groups = store.list_groups()
            assert "g1" in groups
            assert "g1/sub" in groups

    def test_has(self, tmp_h5):
        with Store(tmp_h5, mode="w") as store:
            store.write_dataset("exists", np.array([1]))

        with Store(tmp_h5, mode="r") as store:
            assert store.has("exists")
            assert not store.has("missing")

    def test_not_open_raises(self, tmp_h5):
        store = Store(tmp_h5)
        with pytest.raises(RuntimeError, match="Store not open"):
            _ = store.file

    def test_structured_array(self, tmp_h5):
        dt = np.dtype([("name", "S32"), ("value", "f8")])
        data = np.array(
            [
                (b"alpha", 1.5),
                (b"beta", 2.7),
            ],
            dtype=dt,
        )

        with Store(tmp_h5, mode="w") as store:
            store.write_dataset("records", data)

        with Store(tmp_h5, mode="r") as store:
            result = store.read_dataset("records")
            assert result[0]["name"] == b"alpha"
            assert result[1]["value"] == pytest.approx(2.7)
