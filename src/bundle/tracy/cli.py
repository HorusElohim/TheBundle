# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
bundle tracy CLI

  bundle tracy build                              — build extension + capture + csvexport
  bundle tracy build extension                   — only build the Python extension
  bundle tracy build profiler                    — only build the Tracy viewer GUI
  bundle tracy build capture csvexport           — build specific native tools
  bundle tracy build extension capture csvexport — build everything except profiler
"""

import multiprocessing
import sys
from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer
from bundle.pybind.services.cmake import CMakeService

log = logger.get_logger(__name__)

# Root of TheBundle repo (two levels up from this file)
_BUNDLE_ROOT = Path(__file__).parent.parent.parent.parent
_TRACY_VENDOR = Path(__file__).parent / "vendor" / "tracy"
_VENV_PREFIX = Path(sys.prefix)


@click.group()
@tracer.Sync.decorator.call_raise
async def tracy():
    """Tracy profiler — build extension and native tools."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _build_ext(jobs: int) -> None:
    """Build the bundle.tracy._tracy_ext pybind11 extension.

    Uses ``bundle.pybind`` to resolve and build the extension from the
    tracy-local ``pyproject.toml`` / ``setup.py``.

    After building, the artifact is copied from ``build/lib.<platform>/``
    into ``src/bundle/tracy/`` so it is immediately importable in editable
    installs.  On Windows the target ``.pyd`` may be locked if the current
    process has already imported it — in that case a warning is logged and
    a Python restart is needed.
    """
    import glob
    import shutil

    from bundle.pybind import Pybind

    tracy_dir = Path(__file__).parent
    await Pybind.build(str(tracy_dir), parallel=jobs)

    # Copy the built artifact next to __init__.py for immediate use.
    pattern = str(tracy_dir / "build" / "lib.*" / "_tracy_ext*")
    artifacts = glob.glob(pattern)
    if artifacts:
        src = Path(artifacts[0])
        dst = tracy_dir / src.name
        try:
            shutil.copy2(src, dst)
            log.info("Installed %s → %s", src.name, dst)
        except PermissionError:
            log.warning(
                "Cannot overwrite %s (file in use) — restart Python to pick up the new build",
                dst,
            )


async def _build_tool(name: str, jobs: int, extra_cmake_args: list[str] | None = None) -> None:
    """Build a Tracy CLI tool and install it to the active venv prefix."""
    source_dir = _TRACY_VENDOR / name
    if not source_dir.exists():
        log.warning("Tracy tool source not found: %s (submodule initialised?)", source_dir)
        return

    log.info("Building tracy-%s ...", name)
    # Use a short absolute path to avoid Windows MAX_PATH issues with deeply
    # nested FetchContent artefacts inside the vendor tree.
    build_dir = str(_BUNDLE_ROOT / "build" / f"tracy-{name}")

    # On Windows venv executables live in Scripts/, not bin/.
    extra = list(extra_cmake_args or [])
    if sys.platform == "win32":
        extra.append("-DCMAKE_INSTALL_BINDIR=Scripts")

    await CMakeService.configure(
        source_dir=source_dir,
        build_dir_name=build_dir,
        install_prefix=_VENV_PREFIX,
        extra_args=extra,
    )
    await CMakeService.build(
        source_dir=source_dir,
        build_dir_name=build_dir,
        target="install",
        extra_args=["--parallel", str(jobs)],
    )
    log.info("tracy-%s installed to %s", name, _VENV_PREFIX)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


_ALL_TARGETS = ("extension", "capture", "csvexport")
_VALID_TARGETS = ("extension", "profiler", "capture", "csvexport")


@tracy.command()
@click.argument("targets", nargs=-1, type=click.Choice(_VALID_TARGETS, case_sensitive=False))
@click.option(
    "--jobs",
    "-j",
    type=int,
    default=multiprocessing.cpu_count(),
    show_default=True,
    help="Parallel build jobs.",
)
@tracer.Sync.decorator.call_raise
async def build(targets: tuple[str, ...], jobs: int) -> None:
    """
    Build Tracy components.

    TARGETS: one or more of extension, profiler, capture, csvexport.
    Defaults to: extension capture csvexport.

    \b
    Examples:
      bundle tracy build                        # extension + capture + csvexport
      bundle tracy build extension              # Python binding only
      bundle tracy build profiler               # Tracy viewer GUI (needs GLFW, freetype, capstone)
      bundle tracy build capture csvexport      # native tools only
    """
    selected = list(targets) if targets else list(_ALL_TARGETS)

    for target in selected:
        if target == "extension":
            log.info("Building bundle.tracy._tracy_ext ...")
            await _build_ext(jobs)
        else:
            await _build_tool(target, jobs)

    log.info("Done: %s", ", ".join(selected))
