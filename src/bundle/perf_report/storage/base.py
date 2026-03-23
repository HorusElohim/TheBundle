# Copyright 2026 HorusElohim

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

"""Shared HDF5 storage utilities for performance data."""

from __future__ import annotations

import time
from pathlib import Path

from ...hdf5 import Store

# Max byte lengths for fixed-size string columns in the structured array
MAX_NAME_LEN = 128
MAX_FILE_LEN = 256
MAX_FUNC_LEN = 128


def safe_key(text: str) -> str:
    """Make a string safe for use as an HDF5 group key (no slashes)."""
    return text.replace("/", "_").replace("\\", "_")


def run_prefix(version: str, platform_id: str) -> str:
    return f"{safe_key(version)}/{safe_key(platform_id)}"


def write_meta(
    store: Store,
    prefix: str,
    machine_id: str,
    bundle_version: str,
    platform_id: str,
    platform_meta: dict | None = None,
):
    """Write metadata attributes under the given prefix."""
    meta = {
        "machine_id": machine_id,
        "platform_id": platform_id,
        "bundle_version": bundle_version,
        "timestamp": time.time(),
    }
    if platform_meta:
        meta.update(platform_meta)
    store.write_attrs(f"{prefix}/meta", meta)


def list_versions(h5_path: Path) -> list[str]:
    """List all stored version keys."""
    with Store(h5_path, mode="r") as store:
        return list(store.file.keys())


def list_platforms(h5_path: Path, version: str) -> list[str]:
    """List all platform IDs stored under a version."""
    key = safe_key(version)
    with Store(h5_path, mode="r") as store:
        if key not in store.file:
            return []
        return list(store.file[key].keys())


def load_meta(h5_path: Path, version: str, platform_id: str) -> dict:
    """Read the metadata for a specific version+platform run."""
    prefix = run_prefix(version, platform_id)
    with Store(h5_path, mode="r") as store:
        return store.read_attrs(f"{prefix}/meta")
