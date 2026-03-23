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

from bundle.perf_report import ProfileExtractor

_CSV_HEADER = (
    "name,src_file,src_line,total_ns,total_perc,counts,mean_ns,min_ns,max_ns,std_ns\n"
)
_CSV_ROWS = (
    "my_func,/src/bundle/foo.py,10,1000000,50.0,10,100000,80000,150000,20000.0\n"
    "other_func,/src/bundle/bar.py,20,500000,25.0,5,100000,90000,120000,10000.0\n"
)


@pytest.fixture
def sample_csv(tmp_path) -> Path:
    """Write a minimal Tracy CSV file."""
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(_CSV_HEADER + _CSV_ROWS, encoding="utf-8")
    return csv_path


@pytest.fixture
def sample_csv_dir(tmp_path) -> Path:
    """Write two Tracy CSV files into a directory."""
    for name in ("func_a", "func_b"):
        (tmp_path / f"{name}.csv").write_text(
            _CSV_HEADER
            + f"{name},/src/bundle/{name}.py,1,800000,40.0,8,100000,90000,110000,5000.0\n",
            encoding="utf-8",
        )
    return tmp_path


class TestProfileExtractor:
    def test_extract_single(self, sample_csv):
        profile = ProfileExtractor.extract(sample_csv)
        assert profile.csv_path == sample_csv
        assert profile.name == "sample"
        assert len(profile.records) == 2
        assert profile.total_calls == 15

    def test_records_sorted_by_total_ns(self, sample_csv):
        profile = ProfileExtractor.extract(sample_csv)
        times = [r.total_ns for r in profile.records]
        assert times == sorted(times, reverse=True)

    def test_record_fields(self, sample_csv):
        profile = ProfileExtractor.extract(sample_csv)
        rec = profile.records[0]
        assert isinstance(rec.name, str)
        assert isinstance(rec.src_file, str)
        assert isinstance(rec.src_line, int)
        assert isinstance(rec.total_ns, int)
        assert isinstance(rec.total_perc, float)
        assert isinstance(rec.counts, int)
        assert isinstance(rec.mean_ns, int)
        assert isinstance(rec.min_ns, int)
        assert isinstance(rec.max_ns, int)
        assert isinstance(rec.std_ns, float)

    def test_extract_all_from_directory(self, sample_csv_dir):
        profiles = ProfileExtractor.extract_all(sample_csv_dir)
        assert len(profiles) == 2
        names = {p.name for p in profiles}
        assert "func_a" in names
        assert "func_b" in names

    def test_extract_all_from_single_file(self, sample_csv):
        profiles = ProfileExtractor.extract_all(sample_csv)
        assert len(profiles) == 1
        assert profiles[0].name == "sample"

    def test_extract_all_empty_dir(self, tmp_path):
        profiles = ProfileExtractor.extract_all(tmp_path)
        assert profiles == []
