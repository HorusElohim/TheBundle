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

import os
import pstats
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProfileRecord:
    """A single function entry from a .prof file."""

    file: str
    line_number: int
    function: str
    call_count: int
    total_time: float
    cumulative_time: float


@dataclass
class ProfileData:
    """All records extracted from one .prof file."""

    prof_path: Path
    records: list[ProfileRecord] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.prof_path.stem

    @property
    def total_calls(self) -> int:
        return sum(r.call_count for r in self.records)


class ProfileExtractor:
    """Extract profiling data from .prof files produced by cProfile."""

    @staticmethod
    def extract(prof_path: Path) -> ProfileData:
        """Parse a single .prof file and return structured data."""
        stats = pstats.Stats(str(prof_path))
        stats.strip_dirs().sort_stats("cumulative")
        profile = ProfileData(prof_path=prof_path)
        for (file, line, func_name), (cc, nc, tt, ct, callers) in stats.stats.items():
            profile.records.append(
                ProfileRecord(
                    file=file,
                    line_number=line,
                    function=func_name,
                    call_count=cc,
                    total_time=tt,
                    cumulative_time=ct,
                )
            )
        profile.records.sort(key=lambda r: r.cumulative_time, reverse=True)
        return profile

    @staticmethod
    def extract_all(directory: Path) -> list[ProfileData]:
        """Recursively find and extract all .prof files in a directory."""
        profiles = []
        for root, _, files in os.walk(directory):
            for f in files:
                if f.endswith(".prof"):
                    prof_path = Path(root) / f
                    profiles.append(ProfileExtractor.extract(prof_path))
        return profiles
