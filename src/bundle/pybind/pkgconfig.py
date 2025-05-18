import functools
import os
import shlex
import sys
from pathlib import Path
from typing import List, Tuple

from bundle.core import logger, tracer
from bundle.core.process import Process

log = logger.get_logger(__name__)


class PkgConfig:
    """A utility class for pkg-config operations."""

    @staticmethod
    def set_path(*paths: Path) -> None:
        """
        Sets the PKG_CONFIG_PATH environment variable in a cross-platform manner.

        Parameters:
        - paths: One or more Path objects representing directories to include in PKG_CONFIG_PATH.
        """
        path_sep = ";" if sys.platform == "win32" else ":"
        new_paths = [str(p) for p in paths]
        existing = os.environ.get("PKG_CONFIG_PATH", "")
        if existing:
            # Ensure new_paths are prepended and de-duplicated if necessary,
            # though current logic simply prepends.
            # For robust de-duplication, one might split `existing`, filter, and rejoin.
            # Current behavior: new_paths + existing_paths
            current_existing_list = [p for p in existing.split(path_sep) if p]
            final_paths = new_paths
            for p in current_existing_list:
                if p not in final_paths:
                    final_paths.append(p)
            combined = path_sep.join(final_paths)

        else:
            combined = path_sep.join(new_paths)
        os.environ["PKG_CONFIG_PATH"] = combined
        log.debug(f"PKG_CONFIG_PATH set to: {os.environ['PKG_CONFIG_PATH']}")

    @staticmethod
    def parse_cflags(cflags: str) -> Tuple[List[str], List[str]]:
        flags = shlex.split(cflags)
        inc = [f[2:] for f in flags if f.startswith("-I")]
        other = [f for f in flags if not f.startswith("-I")]
        log.debug(f"Parsed cflags: include_dirs={inc}, other_flags={other}")
        return inc, other

    @staticmethod
    def parse_libs(libs: str) -> Tuple[List[str], List[str], List[str]]:
        flags = shlex.split(libs)
        lib_dirs = [f[2:] for f in flags if f.startswith("-L")]
        names = [f[2:] for f in flags if f.startswith("-l")]
        other = [f for f in flags if not (f.startswith("-L") or f.startswith("-l"))]
        log.debug(f"Parsed libs: lib_dirs={lib_dirs}, libraries={names}, other_flags={other}")
        return lib_dirs, names, other

    @staticmethod
    @functools.lru_cache()
    def run(
        pkg_packages: Tuple[str, ...], pkg_dirs: Tuple[str, ...]
    ) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
        """
        Run pkg-config via the Process wrapper for the given packages and search dirs.
        Caches results to avoid redundant calls.

        Returns: (include_dirs, compile_flags, library_dirs, libraries, link_flags)
        """
        env = os.environ.copy()  # Captures current PKG_CONFIG_PATH state for the subprocess
        # If pkg_dirs are provided, PkgConfig.set_path will modify the *current* process's
        # os.environ["PKG_CONFIG_PATH"]. The subprocess launched by Process() will inherit this.
        if pkg_dirs:
            # Convert tuple of strings to tuple of Path objects for set_path
            path_objects = tuple(Path(p) for p in pkg_dirs)
            PkgConfig.set_path(*path_objects)
            # Update env for the subprocess to reflect changes made by set_path
            env["PKG_CONFIG_PATH"] = os.environ.get("PKG_CONFIG_PATH", "")

        pkgs = " ".join(pkg_packages)
        # build the commands
        cflags_cmd = f"pkg-config --cflags {pkgs}"
        libs_cmd = f"pkg-config --libs {pkgs}"

        # run them
        process = Process()
        # Pass the potentially modified env to the subprocess
        result_c = tracer.Sync.call_raise(process.__call__, cflags_cmd, env=env)
        if result_c.returncode != 0:
            raise RuntimeError(f"pkg-config cflags failed: {result_c.stderr.strip()}")
        result_l = tracer.Sync.call_raise(process.__call__, libs_cmd, env=env)
        if result_l.returncode != 0:
            raise RuntimeError(f"pkg-config libs failed: {result_l.stderr.strip()}")

        log.debug(f"pkg-config cflags output: {result_c.stdout.strip()}")
        log.debug(f"pkg-config libs   output: {result_l.stdout.strip()}")

        inc_dirs, compile_flags = PkgConfig.parse_cflags(result_c.stdout.strip())
        lib_dirs, libraries, link_flags = PkgConfig.parse_libs(result_l.stdout.strip())

        return inc_dirs, compile_flags, lib_dirs, libraries, link_flags
