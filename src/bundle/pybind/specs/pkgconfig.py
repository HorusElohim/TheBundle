from bundle.core import data


class PkgConfigSpec(data.Data):
    """
    This class defines the configuration options for the pkg-config dependency of a pybind11 extension module.
    Attributes:
        packages (list[str]): A list of package names to be resolved using pkg-config.
        extra_dirs (list[str]): A list of directories to search for pkg-config files.
    """

    packages: list[str] = data.Field(default_factory=list)
    extra_dirs: list[str] = data.Field(default_factory=list)
