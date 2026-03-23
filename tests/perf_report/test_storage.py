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

from pathlib import Path

import pytest

from bundle.perf_report import ProfileExtractor, ProfileStorage

VERSION = "0.1.dev1"
PLATFORM = "linux-x86_64-CPython3.12.8"

_CSV_HEADER = "name,src_file,src_line,total_ns,total_perc,counts,mean_ns,min_ns,max_ns,std_ns\n"


@pytest.fixture
def csv_dir(tmp_path) -> Path:
    """Write two Tracy CSV files for testing."""
    for name in ("test_alpha", "test_beta"):
        csv_path = tmp_path / "profiles" / f"{name}.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(
            _CSV_HEADER + f"{name}_func,/src/bundle/{name}.py,1,800000,40.0,8,100000,90000,110000,5000.0\n",
            encoding="utf-8",
        )
    return tmp_path / "profiles"


@pytest.fixture
def h5_path(tmp_path) -> Path:
    return tmp_path / "perf.h5"


class TestProfileStorage:
    def test_save_and_load_meta(self, csv_dir, h5_path):
        profiles = ProfileExtractor.extract_all(csv_dir)
        storage = ProfileStorage(h5_path)
        storage.save(
            profiles,
            machine_id="test-machine-001",
            bundle_version=VERSION,
            platform_id=PLATFORM,
        )

        meta = storage.load_meta(VERSION, PLATFORM)
        assert meta["machine_id"] == "test-machine-001"
        assert meta["bundle_version"] == VERSION
        assert meta["platform_id"] == PLATFORM
        assert "timestamp" in meta

    def test_save_and_load_profiles(self, csv_dir, h5_path):
        profiles = ProfileExtractor.extract_all(csv_dir)
        storage = ProfileStorage(h5_path)
        storage.save(profiles, machine_id="m1", bundle_version=VERSION, platform_id=PLATFORM)

        loaded = storage.load_profiles(VERSION, PLATFORM)
        assert len(loaded) == 2

        for profile in loaded:
            assert len(profile.records) > 0
            rec = profile.records[0]
            assert rec.name
            assert rec.src_file
            assert rec.counts > 0

    def test_save_with_platform_meta(self, csv_dir, h5_path):
        profiles = ProfileExtractor.extract_all(csv_dir)
        storage = ProfileStorage(h5_path)
        pmeta = {"system": "linux", "arch": "x86_64", "python_compiler": "GCC 12.2"}
        storage.save(
            profiles,
            machine_id="m1",
            bundle_version=VERSION,
            platform_id=PLATFORM,
            platform_meta=pmeta,
        )

        meta = storage.load_meta(VERSION, PLATFORM)
        assert meta["system"] == "linux"
        assert meta["arch"] == "x86_64"
        assert meta["python_compiler"] == "GCC 12.2"

    def test_list_versions_and_platforms(self, csv_dir, h5_path):
        profiles = ProfileExtractor.extract_all(csv_dir)
        storage = ProfileStorage(h5_path)
        storage.save(profiles, machine_id="m1", bundle_version="1.0.0", platform_id=PLATFORM)
        storage.save(profiles, machine_id="m2", bundle_version="1.1.0", platform_id=PLATFORM)

        versions = storage.list_versions()
        assert "1.0.0" in versions
        assert "1.1.0" in versions

        platforms = storage.list_platforms("1.0.0")
        assert PLATFORM in platforms

    def test_from_directory(self, csv_dir, h5_path):
        storage = ProfileStorage.from_directory(
            prof_dir=csv_dir,
            h5_path=h5_path,
            machine_id="ci-runner-42",
            bundle_version="0.2.0",
            platform_id=PLATFORM,
        )
        meta = storage.load_meta("0.2.0", PLATFORM)
        assert meta["machine_id"] == "ci-runner-42"
        assert meta["bundle_version"] == "0.2.0"
        assert len(storage.load_profiles("0.2.0", PLATFORM)) == 2

    def test_roundtrip_values(self, csv_dir, h5_path):
        profiles = ProfileExtractor.extract_all(csv_dir)
        storage = ProfileStorage(h5_path)
        storage.save(profiles, machine_id="m1", bundle_version=VERSION, platform_id=PLATFORM)

        loaded = storage.load_profiles(VERSION, PLATFORM)
        assert len(loaded) == len(profiles)

        for orig, back in zip(  # noqa: B905
            sorted(profiles, key=lambda p: p.name),
            sorted(loaded, key=lambda p: p.name),
        ):
            assert len(back.records) == len(orig.records)
            rec = orig.records[0]
            row = back.records[0]
            assert row.counts == rec.counts
            assert row.total_ns == rec.total_ns
            assert row.mean_ns == rec.mean_ns
