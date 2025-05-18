from bundle.core import data

from . import PkgConfigSpec


class ModuleSpec(data.Data):
    """
    This class defines the configuration options required to build a pybind11 extension module.
    It encapsulates all relevant build parameters, such as source files, language standard,
    compiler and linker arguments, and package configuration dependencies.
    """

    name: str
    sources: list[str]
    language: str = "c++"
    cpp_std: str = "20"
    pkgconfig: PkgConfigSpec = data.Field(default_factory=PkgConfigSpec)
    extra_compile_args: list[str] = data.Field(default_factory=list)
    extra_link_args: list[str] = data.Field(default_factory=list)
