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

import time
from pathlib import Path

import numpy as np

from ..hdf5 import Store
from .extractor import ProfileData, ProfileExtractor, ProfileRecord


# Max byte lengths for fixed-size string columns in the structured array
_MAX_FILE_LEN = 256
_MAX_FUNC_LEN = 128


def _profile_dtype() -> np.dtype:
    """Structured dtype for a single profile function record."""
    return np.dtype(
        [
            ("file", f"S{_MAX_FILE_LEN}"),
            ("line_number", "i4"),
            ("function", f"S{_MAX_FUNC_LEN}"),
            ("call_count", "i4"),
            ("total_time", "f8"),
            ("cumulative_time", "f8"),
        ]
    )


def _safe_key(text: str) -> str:
    """Make a string safe for use as an HDF5 group key (no slashes)."""
    return text.replace("/", "_").replace("\\", "_")


class ProfileStorage:
    """Store and retrieve profile data in HDF5, keyed by version and platform.

    HDF5 layout::

        /<version>/<platform_id>/meta       (attrs: machine_id, platform_id, bundle_version, timestamp)
        /<version>/<platform_id>/profiles/<prof_name>  (structured dataset)

    This allows accumulating runs across versions and platforms in a single file.
    """

    def __init__(self, h5_path: Path | str):
        self.h5_path = Path(h5_path)

    @staticmethod
    def _run_prefix(version: str, platform_id: str) -> str:
        return f"{_safe_key(version)}/{_safe_key(platform_id)}"

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
        prefix = self._run_prefix(bundle_version, platform_id)

        meta = {
            "machine_id": machine_id,
            "platform_id": platform_id,
            "bundle_version": bundle_version,
            "timestamp": time.time(),
        }
        if platform_meta:
            meta.update(platform_meta)

        with Store(self.h5_path, mode=mode) as store:
            # Clean existing run data if re-saving same version+platform
            if store.has(prefix):
                del store.file[prefix]

            store.write_attrs(f"{prefix}/meta", meta)

            dt = _profile_dtype()
            for profile in profiles:
                records = np.array(
                    [
                        (
                            r.file.encode("utf-8", errors="replace")[:_MAX_FILE_LEN],
                            r.line_number,
                            r.function.encode("utf-8", errors="replace")[:_MAX_FUNC_LEN],
                            r.call_count,
                            r.total_time,
                            r.cumulative_time,
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
                        "prof_path": str(profile.prof_path),
                        "total_calls": profile.total_calls,
                    },
                )

    def list_versions(self) -> list[str]:
        """List all stored version keys."""
        with Store(self.h5_path, mode="r") as store:
            return list(store.file.keys())

    def list_platforms(self, version: str) -> list[str]:
        """List all platform IDs stored under a version."""
        key = _safe_key(version)
        with Store(self.h5_path, mode="r") as store:
            if key not in store.file:
                return []
            return list(store.file[key].keys())

    def load_meta(self, version: str, platform_id: str) -> dict:
        """Read the metadata for a specific version+platform run."""
        prefix = self._run_prefix(version, platform_id)
        with Store(self.h5_path, mode="r") as store:
            return store.read_attrs(f"{prefix}/meta")

    def load_profiles(self, version: str, platform_id: str) -> list[ProfileData]:
        """Load all profiles for a specific version+platform."""
        prefix = self._run_prefix(version, platform_id)
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
                        file=row["file"].decode("utf-8", errors="replace"),
                        line_number=int(row["line_number"]),
                        function=row["function"].decode("utf-8", errors="replace"),
                        call_count=int(row["call_count"]),
                        total_time=float(row["total_time"]),
                        cumulative_time=float(row["cumulative_time"]),
                    )
                    for row in arr
                ]
                records.sort(key=lambda r: r.cumulative_time, reverse=True)
                profiles.append(
                    ProfileData(
                        prof_path=Path(attrs.get("prof_path", name)),
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
        """Extract all .prof files from a directory and save to HDF5."""
        profiles = ProfileExtractor.extract_all(prof_dir)
        storage = cls(h5_path)
        storage.save(profiles, machine_id, bundle_version, platform_id, platform_meta)
        return storage
