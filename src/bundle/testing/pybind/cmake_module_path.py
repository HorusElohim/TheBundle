from pathlib import Path
from bundle.core import data, logger

log = logger.get_logger(__name__)


class CppModulePath(data.Data):
    source: Path
    build: Path | None = None
    install: Path | None = None
    pkgconfig: Path | None = None

    @data.model_validator(mode="after")
    def _init_(cls, cpp_module_path):
        """
        Validates the CppModulePath instance after initialization.

        Args:
            cpp_module_path: The CppModulePath instance being validated.

        Returns:
            The unchanged CppModulePath instance.
        """
        cpp_module_path.source = cpp_module_path.source.resolve().absolute()
        cpp_module_path.build = cpp_module_path.source / "build"
        cpp_module_path.install = cpp_module_path.source / "install"
        cpp_module_path.pkgconfig = cpp_module_path.install / "lib" / "pkgconfig"

        log.testing("Initialized CppModulePath: %s", log.pretty_repr(cpp_module_path))

        return cpp_module_path
