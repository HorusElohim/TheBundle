from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from bundle.core import platform_info
from bundle.core.process import Process


def _get_platform_specific_cmake_args_env() -> tuple[list[str], dict]:
    """Gets platform-specific CMake arguments and environment variables."""
    env = os.environ.copy()
    cmake_args: list[str] = []
    if platform_info.is_darwin:
        cmake_args.append(f"-DCMAKE_OSX_ARCHITECTURES={platform_info.arch}")
        env["ARCHFLAGS"] = f"-arch {platform_info.arch}"
        env["MACOSX_DEPLOYMENT_TARGET"] = str(platform_info.darwin.macosx_deployment_target)
    return cmake_args, env


class CMakeService:
    """A utility class for running CMake commands."""

    class BuildType(Enum):
        """Enum-like class for CMake build types."""

        DEBUG = "Debug"
        RELEASE = "Release"
        RELWITHDEBINFO = "RelWithDebInfo"
        MINSIZEREL = "MinSizeRel"

    @staticmethod
    async def configure(
        source_dir: Path,
        build_dir_name: str,
        install_prefix: Path | None = None,
        build_type: BuildType = BuildType.RELEASE,
        extra_args: list[str] | None = None,
    ) -> None:
        """
        Configures a CMake project.

        Args:
            source_dir: The root directory of the source code (contains CMakeLists.txt).
            build_dir_name: The name of the build directory, relative to source_dir.
            install_prefix: Optional path for CMAKE_INSTALL_PREFIX.
            extra_args: Optional list of extra arguments to pass to cmake.
        """
        cmd = ["cmake", "-S", ".", "-B", build_dir_name, "-DCMAKE_BUILD_TYPE=" + build_type.value]

        if install_prefix:
            cmd.append(f"-DCMAKE_INSTALL_PREFIX={install_prefix.resolve()}")

        platform_args, env = _get_platform_specific_cmake_args_env()
        cmd.extend(platform_args)

        if extra_args:
            cmd.extend(extra_args)

        proc = Process(name="CMakeService.configure")
        await proc(" ".join(cmd), cwd=str(source_dir), env=env)

    @staticmethod
    async def build(
        source_dir: Path,
        build_dir_name: str,
        target: str | None = None,
        build_type: BuildType = BuildType.RELEASE,
        extra_args: list[str] | None = None,
    ) -> None:
        """
        Builds a CMake project.

        Args:
            source_dir: The root directory of the source code (used as CWD for the command).
            build_dir_name: The name of the build directory, relative to source_dir.
            target: Optional build target (e.g., "install").
            extra_args: Optional list of extra arguments to pass to cmake --build.
        """
        cmd = ["cmake", "--build", build_dir_name, "--config", build_type.value]

        if target:
            cmd.append("--target")
            cmd.append(target)

        if extra_args:
            cmd.extend(extra_args)

        _platform_args, env = _get_platform_specific_cmake_args_env()

        proc = Process(name="CMakeService.build")
        await proc(" ".join(cmd), cwd=str(source_dir), env=env)
