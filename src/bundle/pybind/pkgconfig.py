import functools
import os
import shlex
import sys
from pathlib import Path
from typing import List, Tuple

from bundle.core import logger, tracer
from bundle.core.process import Process

log = logger.get_logger(__name__)


def set_pkg_config_path(*paths: Path) -> None:
    """
    Sets the PKG_CONFIG_PATH environment variable in a cross-platform manner.

    Parameters:
    - paths: One or more Path objects representing directories to include in PKG_CONFIG_PATH.
    """
    path_sep = ";" if sys.platform == "win32" else ":"
    new_paths = [str(p) for p in paths]
    existing = os.environ.get("PKG_CONFIG_PATH", "")
    if existing:
        combined = path_sep.join(new_paths + [existing])
    else:
        combined = path_sep.join(new_paths)
    os.environ["PKG_CONFIG_PATH"] = combined


def parse_cflags(cflags: str) -> Tuple[List[str], List[str]]:
    flags = shlex.split(cflags)
    inc = [f[2:] for f in flags if f.startswith("-I")]
    other = [f for f in flags if not f.startswith("-I")]
    log.debug(f"Parsed cflags: include_dirs={inc}, other_flags={other}")
    return inc, other


def parse_libs(libs: str) -> Tuple[List[str], List[str], List[str]]:
    flags = shlex.split(libs)
    lib_dirs = [f[2:] for f in flags if f.startswith("-L")]
    names = [f[2:] for f in flags if f.startswith("-l")]
    other = [f for f in flags if not (f.startswith("-L") or f.startswith("-l"))]
    log.debug(f"Parsed libs: lib_dirs={lib_dirs}, libraries={names}, other_flags={other}")
    return lib_dirs, names, other


@functools.lru_cache()
def run_pkg_config_cached(
    pkg_packages: Tuple[str, ...], pkg_dirs: Tuple[str, ...]
) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    """
    Run pkg-config via the Process wrapper for the given packages and search dirs.
    Caches results to avoid redundant calls.

    Returns: (include_dirs, compile_flags, library_dirs, libraries, link_flags)
    """
    env = os.environ.copy()
    if pkg_dirs:
        set_pkg_config_path(*pkg_dirs)

    pkgs = " ".join(pkg_packages)
    # build the commands
    cflags_cmd = f"pkg-config --cflags {pkgs}"
    libs_cmd = f"pkg-config --libs {pkgs}"

    # run them
    process = Process()
    result_c = tracer.Sync.call_raise(process.__call__, cflags_cmd, env=env)
    if result_c.returncode != 0:
        raise RuntimeError(f"pkg-config cflags failed: {result_c.stderr.strip()}")
    result_l = tracer.Sync.call_raise(process.__call__, libs_cmd, env=env)
    if result_l.returncode != 0:
        raise RuntimeError(f"pkg-config libs failed: {result_l.stderr.strip()}")

    log.debug(f"pkg-config cflags output: {result_c.stdout.strip()}")
    log.debug(f"pkg-config libs   output: {result_l.stdout.strip()}")

    inc_dirs, compile_flags = parse_cflags(result_c.stdout.strip())
    lib_dirs, libraries, link_flags = parse_libs(result_l.stdout.strip())

    return inc_dirs, compile_flags, lib_dirs, libraries, link_flags
