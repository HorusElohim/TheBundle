import os
import sys
import sysconfig
from pathlib import Path

from bundle.core import tracer
from bundle.core.process import Process


def _get_platform_specific_cmake_args_env() -> tuple[list[str], dict]:
    """Gets platform-specific CMake arguments and environment variables."""
    env = os.environ.copy()
    cmake_args: list[str] = []
    if sys.platform == "darwin":
        import platform

        arch = platform.machine()
        cmake_args.append(f"-DCMAKE_OSX_ARCHITECTURES={arch}")
        env["ARCHFLAGS"] = f"-arch {arch}"
        env["MACOSX_DEPLOYMENT_TARGET"] = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET") or "14.0"
    return cmake_args, env


class CMake:
    """A utility class for running CMake commands."""

    @staticmethod
    def configure(
        source_dir: Path,
        build_dir_name: str,
        install_prefix: Path | None = None,
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
        proc = Process()
        cmd = ["cmake", "-S", ".", "-B", build_dir_name]

        if install_prefix:
            cmd.append(f"-DCMAKE_INSTALL_PREFIX={install_prefix.resolve()}")

        platform_args, env = _get_platform_specific_cmake_args_env()
        cmd.extend(platform_args)

        if extra_args:
            cmd.extend(extra_args)

        tracer.Sync.call_raise(proc.__call__, " ".join(cmd), cwd=str(source_dir), env=env)

    @staticmethod
    def build(
        source_dir: Path,
        build_dir_name: str,
        target: str | None = None,
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
        proc = Process()
        cmd = ["cmake", "--build", build_dir_name]

        if target:
            cmd.append("--target")
            cmd.append(target)

        if extra_args:
            cmd.extend(extra_args)

        _platform_args, env = _get_platform_specific_cmake_args_env()

        tracer.Sync.call_raise(proc.__call__, " ".join(cmd), cwd=str(source_dir), env=env)
