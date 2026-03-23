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

"""Tracy CSV profiling data extraction."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProfileRecord:
    """A single zone entry from a Tracy CSV export (tracy-csvexport)."""

    name: str
    src_file: str
    src_line: int
    total_ns: int
    total_perc: float
    counts: int
    mean_ns: int
    min_ns: int
    max_ns: int
    std_ns: float


@dataclass
class ProfileData:
    """All zone records extracted from one Tracy CSV file."""

    csv_path: Path
    records: list[ProfileRecord] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.csv_path.stem

    @property
    def total_calls(self) -> int:
        return sum(r.counts for r in self.records)


class ProfileExtractor:
    """Extract profiling data from Tracy CSV files produced by tracy-csvexport."""

    @staticmethod
    def _parse_rows(reader) -> list[ProfileRecord]:
        records = []
        for row in reader:
            records.append(
                ProfileRecord(
                    name=row["name"],
                    src_file=row["src_file"],
                    src_line=int(row["src_line"]),
                    total_ns=int(float(row["total_ns"])),
                    total_perc=float(row["total_perc"]),
                    counts=int(row["counts"]),
                    mean_ns=int(float(row["mean_ns"])),
                    min_ns=int(float(row["min_ns"])),
                    max_ns=int(float(row["max_ns"])),
                    std_ns=float(row["std_ns"]),
                )
            )
        records.sort(key=lambda r: r.total_ns, reverse=True)
        return records

    @staticmethod
    def extract(csv_path: Path) -> ProfileData:
        """Parse a single Tracy CSV file and return structured data."""
        csv_path = Path(csv_path)
        profile = ProfileData(csv_path=csv_path)
        with open(csv_path, newline="", encoding="utf-8") as f:
            profile.records = ProfileExtractor._parse_rows(csv.DictReader(f))
        return profile

    @staticmethod
    def extract_from_tracy(tracy_path: Path) -> ProfileData:
        """Run tracy-csvexport on a .tracy file, save a sibling .csv, and return ProfileData.

        Requires tracy-csvexport to be on PATH (built via: bundle tracy build csvexport).
        The CSV is saved alongside the .tracy file so it can be reused without re-exporting.
        """
        import shutil
        import subprocess

        tracy_path = Path(tracy_path)
        csvexport = shutil.which("tracy-csvexport")
        if not csvexport:
            raise FileNotFoundError("tracy-csvexport not found on PATH — run: bundle tracy build csvexport")

        result = subprocess.run([csvexport, str(tracy_path)], capture_output=True, text=True, check=True)

        csv_path = tracy_path.with_suffix(".csv")
        csv_path.write_text(result.stdout, encoding="utf-8")
        return ProfileExtractor.extract(csv_path)

    @staticmethod
    def extract_all(path: Path) -> list[ProfileData]:
        """Extract from a .tracy file, a single CSV file, or all CSV files in a directory."""
        path = Path(path)
        if path.is_file():
            if path.suffix == ".tracy":
                return [ProfileExtractor.extract_from_tracy(path)]
            return [ProfileExtractor.extract(path)]
        return [ProfileExtractor.extract(f) for f in sorted(path.glob("*.csv"))]
