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

from pathlib import Path

import toml

from bundle.core import logger

log = logger.get_logger(__name__)


def discover_project(source_dir: Path) -> dict:
    """Read pyproject.toml and return project metadata and package layout.

    Args:
        source_dir: Project root directory containing pyproject.toml.

    Returns:
        Dictionary with keys: name, version, author, package_dirs.
    """
    pyproject_path = source_dir / "pyproject.toml"
    result = {
        "name": source_dir.name,
        "version": "",
        "author": "",
        "package_dirs": [],
    }

    if not pyproject_path.exists():
        log.warning("No pyproject.toml found at %s, using defaults", source_dir)
        # Fallback: look for directories with __init__.py at top level
        for p in source_dir.iterdir():
            if p.is_dir() and (p / "__init__.py").exists():
                result["package_dirs"].append(str(p.relative_to(source_dir)))
        return result

    data = toml.loads(pyproject_path.read_text())
    project = data.get("project", {})

    result["name"] = project.get("name", source_dir.name)
    result["version"] = project.get("version", "")

    authors = project.get("authors", [])
    if authors and isinstance(authors[0], dict):
        result["author"] = authors[0].get("name", "")

    # Discover package directories from setuptools config
    find_cfg = (
        data.get("tool", {}).get("setuptools", {}).get("packages", {}).get("find", {})
    )
    where = find_cfg.get("where", ["."])
    if isinstance(where, str):
        where = [where]

    package_dirs = []
    for w in where:
        src_root = source_dir / w
        if src_root.is_dir():
            for p in src_root.iterdir():
                if p.is_dir() and (p / "__init__.py").exists():
                    package_dirs.append(str(p.relative_to(source_dir)))

    result["package_dirs"] = package_dirs
    log.info("Discovered project: %s (packages: %s)", result["name"], package_dirs)
    return result


def find_readme_files(package_root: Path) -> list[Path]:
    """Recursively find all README.md files in the package tree.

    Args:
        package_root: Root directory of the Python package.

    Returns:
        Sorted list of README.md paths found.
    """
    return sorted(package_root.rglob("README.md"))


def find_subpackages(package_root: Path) -> list[str]:
    """Find all Python subpackages (directories with __init__.py).

    Args:
        package_root: Root directory of the Python package.

    Returns:
        Sorted list of subpackage names.
    """
    subpackages = []
    for p in sorted(package_root.iterdir()):
        if p.is_dir() and (p / "__init__.py").exists():
            subpackages.append(p.name)
    return subpackages
