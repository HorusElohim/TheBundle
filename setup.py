"""
Setup script for TheBundle project.

This script builds several CMake-based components:
  - tracy_bindings: Python bindings for Tracy.
  - tracy_profiler: Executable for profiling.
  - tracy_csvexport: Executable for CSV export.
  - tracy_capture: Executable for capture.
  
The build process uses pathlib for path manipulations and logging
for output messages.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

# Configure logging.
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BUILD_CMD = ["cmake", "--build", ".", "--config", "Release", "--parallel"]


def get_executable_install_dir() -> Path:
    """
    Returns the appropriate directory for installing executables:
      - On Windows, typically the "Scripts" folder.
      - On Unix-like systems, typically the "bin" folder.
    """
    if sys.platform.startswith("win"):
        return Path(sys.prefix) / "Scripts"
    else:
        return Path(sys.prefix) / "bin"


def get_latest_modification_time(directory: Path, exclude_files: list[Path] | None = None) -> float | None:
    """
    Returns the latest modification time among all files in the given directory,
    excluding any files whose resolved paths are in the 'exclude_files' list.
    Also logs the file that has the latest modification time.

    Parameters:
      directory (Path): The directory to scan recursively.
      exclude_files (list[Path] | None): A list of Path objects to ignore (default: None).

    Returns:
      float | None: The latest modification time in seconds since the epoch,
                    or None if no files are found.
    """
    exclude_set = {p.name for p in (exclude_files or [])}
    candidates = [f for f in directory.rglob("*") if f.is_file() and not any(ef in str(f.absolute) for ef in exclude_set)]
    if not candidates:
        return None
    latest_file = max(candidates, key=lambda f: f.stat().st_mtime)
    latest_mtime = latest_file.stat().st_mtime
    logger.info("Latest modified file in %s: %s (mtime: %s)", directory, latest_file, latest_mtime)
    return latest_mtime


def get_system_libs_extension() -> list[str]:
    if sys.platform.startswith("win"):
        return [".pyd", ".dll"]
    if sys.platform == "darwin":
        return [".dylib", ".so"]
    return [".so"]


def get_candidate_files(directory: Path, suffixes: list[str]) -> list[Path]:
    """
    Returns a list of files in the given directory whose suffix is in the provided list.
    """
    return [f for f in directory.iterdir() if f.is_file() and any(s in f.name for s in suffixes)]


def get_min_modification_time(files: list[Path]) -> float | None:
    """
    Returns the minimum modification time among the given files.
    Returns None if the list is empty.
    """
    if not files:
        return None
    return min(f.stat().st_mtime for f in files)


def clean_previous_cmake_build(path: Path):
    if path.exists():
        cmake_cache = path / "CMakeCache.txt"
        cmake_files = path / "CMakeFiles"
        logger.info(f"Removing previous {str(cmake_cache)}")
        cmake_cache.unlink(missing_ok=True)
        logger.info(f"Removing previous {str(cmake_files)}")
        shutil.rmtree(cmake_files, ignore_errors=True)


class CMakeExtension(Extension):
    """
    A setuptools Extension for CMake-based projects.
    """

    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = Path(sourcedir).resolve()


class CMakeBuild(build_ext):
    """
    A custom build_ext command that builds CMake extensions.
    """

    def run(self) -> None:
        try:
            subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError("CMake must be installed to build the Tracy components")
        for ext in self.extensions:
            self.build_extension(ext)
        # Post-build: install the external tracy_client package.
        self.install_tracy_client()

    def build_extension(self, ext: CMakeExtension) -> None:
        """
        Dispatch the build process based on the extension name.
        """
        if self.is_extension_up_to_date(ext):
            logger.info("Extension %s is up-to-date. Skipping build.", ext.name)
            return

        logger.info("Extension %s is need to be built.", ext.name)

        if ext.name == "tracy_bindings":
            self.build_extension_client(ext)
        elif ext.name == "tracy_profiler":
            self.build_extension_profiler(ext)
        elif ext.name == "tracy_csvexport":
            self.build_extension_csvexport(ext)
        elif ext.name == "tracy_capture":
            self.build_extension_capture(ext)
        else:
            raise RuntimeError(f"Unknown extension {ext.name}")

    def get_built_target(self, ext: CMakeExtension) -> Path:
        """
        Returns the expected output file path for the given extension.
        For Python bindings, uses get_ext_fullpath; for executables, uses the
        executable installation directory.
        """
        if ext.name == "tracy_bindings":
            return Path(self.get_ext_fullpath(ext.name))
        else:
            target_dir = get_executable_install_dir()
            filename = ext.name
            if sys.platform.startswith("win"):
                filename += ".exe"
            return target_dir / filename

    def is_extension_up_to_date(self, ext: CMakeExtension) -> bool:
        """
        Returns True if the built target (or, for tracy_bindings,
        all expected library files) exist and are newer than every file in the extension's source directory.
        """
        if ext.name == "tracy_bindings":
            bindings_dir = Path("external") / "native" / "tracy" / "python" / "tracy_client"
            if not bindings_dir.exists():
                return False

            if candidates := get_candidate_files(bindings_dir, get_system_libs_extension()):
                logger.info("Checking %s", str(candidates))
                if latest_source_mtime := get_latest_modification_time(
                    ext.sourcedir, exclude_files=candidates + [Path("__pycache__"), Path("tracy_client.egg-info")]
                ):
                    if min_candidate_mtime := get_min_modification_time(candidates):
                        logger.info("Min time: %s", str(min_candidate_mtime))
                        return min_candidate_mtime >= latest_source_mtime
        else:
            logger.info("Checking %s ", ext.sourcedir)
            excluded_libs = get_candidate_files(ext.sourcedir, get_system_libs_extension())
            if latest_source_mtime := get_latest_modification_time(ext.sourcedir, exclude_files=excluded_libs):
                logger.info("Latest source time %s", str(latest_source_mtime))
                if target_file := self.get_built_target(ext):
                    if not target_file.exists():
                        return False
                    target_mtime = target_file.stat().st_mtime
                    return target_mtime >= latest_source_mtime
        return False

    def build_extension_client(self, ext: CMakeExtension) -> None:
        """
        Build the Python bindings for Tracy.
        """
        cmake_args = [
            f"-DCMAKE_BUILD_TYPE=Release",
            "-DTRACY_CLIENT_PYTHON=ON",
            "-DBUILD_SHARED_LIBS=ON",
            "-DTRACY_STATIC=OFF",
            "-DTRACY_ENABLE=ON",
        ]
        build_temp = Path(self.build_temp) / ext.name
        build_temp.mkdir(parents=True, exist_ok=True)
        logger.info("Building tracy_bindings in %s", build_temp)
        subprocess.check_call(["cmake", str(ext.sourcedir)] + cmake_args, cwd=str(build_temp))
        subprocess.check_call(BUILD_CMD, cwd=str(build_temp))

    def build_extension_profiler(self, ext: CMakeExtension) -> None:
        """
        Build the tracy-profiler executable.
        """
        target_dir = get_executable_install_dir()
        cmake_args = [
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={str(target_dir)}",
            f"-DCMAKE_BUILD_TYPE=Release",
            "-DDOWNLOAD_FREETYPE=ON",
        ]
        if sys.platform.lower() == "linux":
            cmake_args.append("-DLEGACY=ON")
        build_temp = Path(self.build_temp) / "tracy-tools"
        build_temp.mkdir(parents=True, exist_ok=True)
        clean_previous_cmake_build(build_temp)
        logger.info("Building tracy_profiler in %s", build_temp)

        subprocess.check_call(["cmake", str(ext.sourcedir)] + cmake_args, cwd=str(build_temp))
        subprocess.check_call(BUILD_CMD, cwd=str(build_temp))

    def build_extension_csvexport(self, ext: CMakeExtension) -> None:
        """
        Build the tracy_csvexport executable.
        """
        target_dir = get_executable_install_dir()
        cmake_args = [
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={str(target_dir)}",
            f"-DCMAKE_BUILD_TYPE=Release",
        ]
        build_temp = Path(self.build_temp) / "tracy-tools"
        build_temp.mkdir(parents=True, exist_ok=True)
        clean_previous_cmake_build(build_temp)
        logger.info("Building tracy_csvexport in %s", build_temp)
        subprocess.check_call(["cmake", str(ext.sourcedir)] + cmake_args, cwd=str(build_temp))
        subprocess.check_call(BUILD_CMD, cwd=str(build_temp))

    def build_extension_capture(self, ext: CMakeExtension) -> None:
        """
        Build the tracy_capture executable.
        """
        target_dir = get_executable_install_dir()
        cmake_args = [
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={str(target_dir)}",
            f"-DCMAKE_BUILD_TYPE=Release",
        ]
        build_temp = Path(self.build_temp) / "tracy-tools"
        build_temp.mkdir(parents=True, exist_ok=True)
        clean_previous_cmake_build(build_temp)
        logger.info("Building tracy_capture in %s", build_temp)
        subprocess.check_call(["cmake", str(ext.sourcedir)] + cmake_args, cwd=str(build_temp))
        subprocess.check_call(BUILD_CMD, cwd=str(build_temp))

    def install_tracy_client(self) -> None:
        """
        After building the bindings, install the external tracy_client package.
        This triggers a pip install of the package found in external/native/tracy/python.
        """
        logger.info("Running post-build hook: installing external tracy_client package.")
        cmd = [sys.executable, "-m", "pip", "install", "."]
        tracy_python_dir = Path("external") / "native" / "tracy" / "python"
        logger.info("Installing tracy_client from %s ...", tracy_python_dir)
        subprocess.check_call(cmd, cwd=str(tracy_python_dir), env=os.environ.copy())


# Detect whether the "tracy-profiler" extra is requested.
# This flag triggers the build of additional executables:
#  - tracy_profiler, tracy_csvexport, and tracy_capture.
include_tools: bool = os.environ.get("TRACY_TOOLS", "false").lower() in ("1", "true")
logger.info("Build Tracy-Tools: %s", include_tools)

ext_modules = [
    CMakeExtension("tracy_bindings", sourcedir="external/native/tracy"),
]

if include_tools:
    ext_modules.append(CMakeExtension("tracy-profiler", sourcedir="external/native/tracy/profiler"))
    ext_modules.append(CMakeExtension("tracy-csvexport", sourcedir="external/native/tracy/csvexport"))
    ext_modules.append(CMakeExtension("tracy-capture", sourcedir="external/native/tracy/capture"))
else:
    logger.info(
        "Skipping build of tracy_profiler, tracy_csvexport, and tracy_capture. "
        "Use pip install .[tracy-profiler] to include them."
    )

setup(
    name="thebundle",
    ext_modules=ext_modules,
    cmdclass={"build_ext": CMakeBuild},
)
