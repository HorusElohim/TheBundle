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

from pathlib import Path

from ...core.logger import get_logger

logger = get_logger("bundle.testing")


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
            logger.testing("created folder: %s ", path.parent)
    else:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            logger.testing("created folder: %s ", path)
    return path


def class_instance_name(class_instance: object):
    if isinstance(class_instance, str):
        return class_instance
    name = f".{class_instance.name}" if hasattr(class_instance, "name") else ""
    name = f"{name}__{class_instance.__test_name}" if hasattr(class_instance, "__test_name") else name
    return f"{class_instance.__class__.__name__}{name}"


def retrieves_tests_paths(
    category: str,
    ref_dir: str | Path,
    tmp_dir: str | Path,
    class_instance: object,
    suffix: str,
    extension: str = "json",
) -> tuple[Path, Path, Path, Path]:
    """
    Generate and ensure paths for reference, temporary, failed tests, and their logs based on
    the test category, directory references, test instance, and file details.

    Args:
        category (str): A '/' separated string defining the test category hierarchy.
        ref_dir (str | Path): The base directory for reference files.
        tmp_dir (str | Path): The base directory for temporary test files.
        class_instance (object): The test class instance to include in the filename.
        suffix (str): Suffix to append to the base filename, typically a test identifier.
        extension (str, optional): File extension for the test files. Defaults to "json".

    Returns:
        tuple[Path, Path, Path, Path]: A tuple containing paths for reference, temporary,
        failed test files, and failed test logs.
    """

    if isinstance(ref_dir, str):
        ref_dir = Path(ref_dir)
    if isinstance(tmp_dir, str):
        tmp_dir = Path(tmp_dir)

    categories = category.split("/")
    filename = f"{class_instance_name(class_instance)}__{suffix}.{extension}"
    ref_path = ensure_path(ref_dir / "ref" / Path(*categories) / filename)
    tmp_path = ensure_path(tmp_dir / Path(*categories) / filename)
    failed_path = ensure_path(ref_dir / "failed" / Path(*categories) / filename)
    failed_error_log_path = ensure_path(ref_dir / "failed" / Path(*categories) / "logs" / filename)

    return (
        ref_path,
        tmp_path,
        failed_path,
        failed_error_log_path,
    )
