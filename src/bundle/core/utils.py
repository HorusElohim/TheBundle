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

from datetime import datetime, timedelta
from pathlib import Path

from .logger import get_logger

logger = get_logger(__name__)


def ensure_path(path: Path | str) -> Path:
    """
    Ensures existence of a path's directories. For file paths, creates missing parent directories.
    For directory paths, creates the directory if missing. Logs creation actions.

    Args:
        path (Path): Target file or directory path.

    Returns:
        Path: Verified path
    """
    path = Path(path)
    if path.suffix:
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.debug("created folder: %s ", path.parent)
    else:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.debug("created folder: %s ", path)
    return path


def format_duration_ns(ns: int) -> str:
    """
    Formats a duration in nanoseconds to a human-readable string.

    Converts nanoseconds to days, hours, minutes, seconds, milliseconds,
    and microseconds, displaying only the non-zero units.

    Args:
        ns (int): The duration in nanoseconds.

    Returns:
        str: The formatted duration string.
    """
    td = timedelta(microseconds=ns / 1000)

    units = [
        (td.days, "d"),
        (td.seconds // 3600, "h"),
        (td.seconds % 3600 // 60, "m"),
        (td.seconds % 60, "s"),
        (td.microseconds // 1000, "ms"),
        (td.microseconds % 1000, "µs"),  # Add microseconds
    ]

    time_str = ":".join(f"{value}{unit}" for value, unit in units if value > 0)

    # Append remaining nanoseconds for durations less than 1 microsecond
    remaining_ns = ns % 1000
    if remaining_ns > 0:
        time_str += f":{remaining_ns}ns"
    elif time_str == "":
        time_str = f"{ns}ns"

    return time_str


def format_date_ns(ns: int) -> str:
    """
    Converts a timestamp in nanoseconds to a formatted UTC date string.

    Formats the timestamp to include year, month, day, hour, minute, second,
    and extends to show milliseconds, microseconds, and nanoseconds.

    Args:
        ns (int): The timestamp in nanoseconds since the Unix epoch.

    Returns:
        str: The formatted date string in UTC.
    """
    dt = datetime.fromtimestamp(ns // 1_000_000_000)

    # Extract milliseconds, microseconds, and remaining nanoseconds
    milliseconds = (ns // 1_000_000) % 1_000
    microseconds = (ns // 1_000) % 1_000
    nanoseconds = ns % 1_000

    # Format the datetime object with milliseconds, microseconds, and nanoseconds
    return dt.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}.{microseconds:03d}.{nanoseconds:03d}")
