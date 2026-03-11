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

import cProfile
from pathlib import Path

import pytest

from bundle.perf_report import ProfileExtractor


@pytest.fixture
def sample_prof(tmp_path) -> Path:
    """Create a real .prof file by profiling a simple function."""
    prof_path = tmp_path / "sample.prof"
    profiler = cProfile.Profile()
    profiler.enable()
    # Profile some actual work
    _ = sum(range(1000))
    _ = [x**2 for x in range(100)]
    profiler.disable()
    profiler.dump_stats(str(prof_path))
    return prof_path


@pytest.fixture
def sample_prof_dir(tmp_path) -> Path:
    """Create a directory with multiple .prof files."""
    for name in ("func_a", "func_b"):
        prof_path = tmp_path / f"{name}.prof"
        profiler = cProfile.Profile()
        profiler.enable()
        _ = sum(range(500))
        profiler.disable()
        profiler.dump_stats(str(prof_path))
    return tmp_path


class TestProfileExtractor:
    def test_extract_single(self, sample_prof):
        profile = ProfileExtractor.extract(sample_prof)
        assert profile.prof_path == sample_prof
        assert profile.name == "sample"
        assert len(profile.records) > 0
        assert profile.total_calls > 0

    def test_records_sorted_by_cumulative_time(self, sample_prof):
        profile = ProfileExtractor.extract(sample_prof)
        times = [r.cumulative_time for r in profile.records]
        assert times == sorted(times, reverse=True)

    def test_record_fields(self, sample_prof):
        profile = ProfileExtractor.extract(sample_prof)
        rec = profile.records[0]
        assert isinstance(rec.file, str)
        assert isinstance(rec.line_number, int)
        assert isinstance(rec.function, str)
        assert isinstance(rec.call_count, int)
        assert isinstance(rec.total_time, float)
        assert isinstance(rec.cumulative_time, float)

    def test_extract_all(self, sample_prof_dir):
        profiles = ProfileExtractor.extract_all(sample_prof_dir)
        assert len(profiles) == 2
        names = {p.name for p in profiles}
        assert "func_a" in names
        assert "func_b" in names

    def test_extract_all_empty_dir(self, tmp_path):
        profiles = ProfileExtractor.extract_all(tmp_path)
        assert profiles == []
