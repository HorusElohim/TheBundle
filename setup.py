import os
import sys
import subprocess
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


def get_executable_install_dir() -> str:
    """
    Returns the appropriate directory for installing executables:
      - On Windows, it is typically the "Scripts" folder.
      - On Unix-like systems, it is typically the "bin" folder.
    """
    if sys.platform.startswith("win"):
        return os.path.join(sys.prefix, "Scripts")
    else:
        return os.path.join(sys.prefix, "bin")


# Define a simple CMakeExtension (we’re not using sources here)
class CMakeExtension(Extension):
    def __init__(self, name: str, sourcedir: str = "") -> None:
        super().__init__(name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def run(self) -> None:
        try:
            subprocess.check_output(["cmake", "--version"])
        except OSError:
            raise RuntimeError("CMake must be installed to build the Tracy components")
        for ext in self.extensions:
            self.build_extension(ext)
        # Post-build: install the external tracy_client package
        self.install_tracy_client()

    def build_extension(self, ext: CMakeExtension) -> None:
        if ext.name == "tracy_bindings":
            self.build_extension_client(ext)
        elif ext.name == "tracy_profiler":
            self.build_extension_profiler(ext)
        else:
            raise RuntimeError(f"Unknown extension {ext.name}")

    def build_extension_client(self, ext: CMakeExtension) -> None:
        # Build the Python bindings for Tracy
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cfg = "Debug" if self.debug else "Release"
        cmake_args = [
            f"-DCMAKE_BUILD_TYPE={cfg}",
            "-DTRACY_CLIENT_PYTHON=ON",
            "-DBUILD_SHARED_LIBS=ON",
            "-DTRACY_STATIC=OFF",
            "-DTRACY_ENABLE=ON",
        ]
        build_temp = os.path.join(self.build_temp, ext.name)
        os.makedirs(build_temp, exist_ok=True)
        subprocess.check_call(["cmake", ext.sourcedir] + cmake_args, cwd=build_temp)
        subprocess.check_call(["cmake", "--build", ".", "--config", cfg, "--parallel"], cwd=build_temp)

    def build_extension_profiler(self, ext: CMakeExtension) -> None:
        # Build the tracy-profiler executable.
        # Instead of outputting into the package directory, we direct CMake to output the binary into
        # the virtual environment's bin (or Scripts) directory.
        target_dir = get_executable_install_dir()
        cfg = "Debug" if self.debug else "Release"
        cmake_args = [
            f"-DCMAKE_RUNTIME_OUTPUT_DIRECTORY={target_dir}",
            f"-DCMAKE_BUILD_TYPE={cfg}",
        ]
        if sys.platform.lower() == "linux":
            cmake_args.append(f"-DLEGACY=ON")
        build_temp = os.path.join(self.build_temp, ext.name)
        os.makedirs(build_temp, exist_ok=True)
        subprocess.check_call(["cmake", ext.sourcedir] + cmake_args, cwd=build_temp)
        subprocess.check_call(["cmake", "--build", ".", "--config", cfg, "--parallel"], cwd=build_temp)

    def install_tracy_client(self) -> None:
        """
        After building the bindings, install the external Tracy Python package.
        This triggers a pip install of the package found in external/native/tracy/python.
        """
        print("Running post-build hook: installing external tracy_client package.")
        cmd = [sys.executable, "-m", "pip", "install", "."]
        tracy_python_dir = os.path.join("external", "native", "tracy", "python")
        print(f"Installing tracy_client from {tracy_python_dir} ...")
        subprocess.check_call(cmd, cwd=tracy_python_dir, env=os.environ.copy())


setup(
    name="thebundle",
    ext_modules=[
        CMakeExtension("tracy_bindings", sourcedir="external/native/tracy"),
        CMakeExtension("tracy_profiler", sourcedir="external/native/tracy/profiler"),
    ],
    cmdclass={
        "build_ext": CMakeBuild,
    },
)
