from pathlib import Path

import pybind11

from bundle.core import data

from ...core import platform_info
from ..specs import ModuleSpec
from .pkgconfig import PkgConfigResolved


class ModuleResolved(data.Data):
    """
    This class defines the resolved configuration options required to build a pybind11 extension module.
    In addition of ModuleSpec, add the resolved pkg-config information.
    """

    spec: ModuleSpec
    pkgconfig: PkgConfigResolved = data.Field(default_factory=PkgConfigResolved)

    @property
    def sources(self) -> list[str]:
        """
        Source files, relative paths.
        """
        return [str(Path(s)) for s in self.spec.sources]

    @property
    def std_flag(self) -> str:
        """
        The compiler flag for the requested C++ standard.
        """
        if platform_info.is_windows:
            return f"/std:c++{self.spec.cpp_std}"
        return f"-std=c++{self.spec.cpp_std}"

    @property
    def include_dirs(self) -> list[str]:
        """
        pybind11 include first, then spec-level dirs, then any pkg-config includes.
        """
        dirs: list[str] = [pybind11.get_include(), *self.spec.include_dirs]
        for pkg in self.pkgconfig.resolved:
            dirs.extend(pkg.include_dirs)
        return dirs

    @property
    def library_dirs(self) -> list[str]:
        """
        All pkg-config library directories.
        """
        dirs: list[str] = []
        for pkg in self.pkgconfig.resolved:
            dirs.extend(pkg.library_dirs)
        return dirs

    @property
    def libraries(self) -> list[str]:
        """
        All pkg-config libraries.
        """
        libs: list[str] = []
        for pkg in self.pkgconfig.resolved:
            libs.extend(pkg.libraries)
        return libs

    @property
    def extra_compile_args(self) -> list[str]:
        """
        std flag, then spec-level args, then pkg-config compile flags.
        """
        args: list[str] = [self.std_flag, *self.spec.extra_compile_args]
        for pkg in self.pkgconfig.resolved:
            args.extend(pkg.compile_flags)
        return args

    @property
    def extra_link_args(self) -> list[str]:
        """
        Spec-level link args, then pkg-config linker flags.
        """
        args: list[str] = [*self.spec.extra_link_args]
        for pkg in self.pkgconfig.resolved:
            args.extend(pkg.link_flags)
        return args
