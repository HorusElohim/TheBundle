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

"""HDF5 storage for Tracy zone profiling data."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ...hdf5 import Store
from ..extractor import ProfileData, ProfileExtractor, ProfileRecord
from .base import MAX_FILE_LEN, MAX_NAME_LEN, list_platforms, list_versions, load_meta, run_prefix, write_meta


def _zone_dtype() -> np.dtype:
    """Structured dtype for a single Tracy zone record."""
    return np.dtype(
        [
            ("name", f"S{MAX_NAME_LEN}"),
            ("src_file", f"S{MAX_FILE_LEN}"),
            ("src_line", "i4"),
            ("total_ns", "i8"),
            ("total_perc", "f8"),
            ("counts", "i4"),
            ("mean_ns", "i8"),
            ("min_ns", "i8"),
            ("max_ns", "i8"),
            ("std_ns", "f8"),
        ]
    )


class ProfileStorage:
    """Store and retrieve Tracy zone data in HDF5, keyed by version and platform.

    HDF5 layout::

        /<version>/<platform_id>/meta       (attrs: machine_id, platform_id, bundle_version, timestamp)
        /<version>/<platform_id>/profiles/<name>  (structured dataset)
    """

    def __init__(self, h5_path: Path | str):
        self.h5_path = Path(h5_path)

    def save(
        self,
        profiles: list[ProfileData],
        machine_id: str,
        bundle_version: str,
        platform_id: str,
        platform_meta: dict | None = None,
    ):
        """Write profiles under /<version>/<platform_id>/, appending to existing file."""
        mode = "a" if self.h5_path.exists() else "w"
        prefix = run_prefix(bundle_version, platform_id)

        with Store(self.h5_path, mode=mode) as store:
            if store.has(prefix):
                del store.file[prefix]

            write_meta(store, prefix, machine_id, bundle_version, platform_id, platform_meta)

            dt = _zone_dtype()
            for profile in profiles:
                records = np.array(
                    [
                        (
                            r.name.encode("utf-8", errors="replace")[:MAX_NAME_LEN],
                            r.src_file.encode("utf-8", errors="replace")[:MAX_FILE_LEN],
                            r.src_line,
                            r.total_ns,
                            r.total_perc,
                            r.counts,
                            r.mean_ns,
                            r.min_ns,
                            r.max_ns,
                            r.std_ns,
                        )
                        for r in profile.records
                    ],
                    dtype=dt,
                )
                dataset_path = f"{prefix}/profiles/{profile.name}"
                store.write_dataset(dataset_path, records)
                store.write_attrs(
                    dataset_path,
                    {
                        "csv_path": str(profile.csv_path),
                        "total_calls": profile.total_calls,
                    },
                )

    def list_versions(self) -> list[str]:
        return list_versions(self.h5_path)

    def list_platforms(self, version: str) -> list[str]:
        return list_platforms(self.h5_path, version)

    def load_meta(self, version: str, platform_id: str) -> dict:
        return load_meta(self.h5_path, version, platform_id)

    def load_profiles(self, version: str, platform_id: str) -> list[ProfileData]:
        """Load all profiles for a specific version+platform."""
        prefix = run_prefix(version, platform_id)
        profiles = []
        with Store(self.h5_path, mode="r") as store:
            profiles_group = f"{prefix}/profiles"
            if not store.has(profiles_group):
                return []
            names = store.list_datasets(profiles_group)
            for name in names:
                dataset_path = f"{profiles_group}/{name}"
                arr = store.read_dataset(dataset_path)
                attrs = store.read_attrs(dataset_path)
                records = [
                    ProfileRecord(
                        name=row["name"].decode("utf-8", errors="replace"),
                        src_file=row["src_file"].decode("utf-8", errors="replace"),
                        src_line=int(row["src_line"]),
                        total_ns=int(row["total_ns"]),
                        total_perc=float(row["total_perc"]),
                        counts=int(row["counts"]),
                        mean_ns=int(row["mean_ns"]),
                        min_ns=int(row["min_ns"]),
                        max_ns=int(row["max_ns"]),
                        std_ns=float(row["std_ns"]),
                    )
                    for row in arr
                ]
                records.sort(key=lambda r: r.total_ns, reverse=True)
                profiles.append(
                    ProfileData(
                        csv_path=Path(attrs.get("csv_path", name)),
                        records=records,
                    )
                )
        return profiles

    @classmethod
    def from_directory(
        cls,
        prof_dir: Path,
        h5_path: Path,
        machine_id: str,
        bundle_version: str,
        platform_id: str,
        platform_meta: dict | None = None,
    ) -> ProfileStorage:
        """Extract all Tracy CSV files from a path and save to HDF5."""
        profiles = ProfileExtractor.extract_all(prof_dir)
        storage = cls(h5_path)
        storage.save(profiles, machine_id, bundle_version, platform_id, platform_meta)
        return storage
