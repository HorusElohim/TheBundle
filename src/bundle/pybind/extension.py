from __future__ import annotations

from pathlib import Path

from setuptools import Extension
from setuptools.command.build_ext import build_ext

from bundle.core import logger, tracer

from .resolved.project import ModuleResolved

log = logger.get_logger(__name__)


class ExtensionSpec(Extension):
    @classmethod
    @tracer.Async.decorator.call_raise
    async def from_module_resolved(cls, module: ModuleResolved) -> ExtensionSpec:
        """
        Create a setuptools.Extension from a resolved module.

        :param module: The ModuleResolved object containing spec + pkgconfig info.
        :return: Configured setuptools.Extension.
        """
        ext = cls(
            name=module.spec.name,
            sources=module.sources,
            language=module.spec.language,
            include_dirs=module.include_dirs,
            library_dirs=module.library_dirs,
            libraries=module.libraries,
            extra_compile_args=module.extra_compile_args,
            extra_link_args=module.extra_link_args,
        )
        ext._build_temp = f"build/temp_{module.spec.name}"
        return ext


class ExtensionBuild(build_ext):
    """A ``build_ext`` command that prunes C/C++ sources after compilation.

    Why is this necessary?
    ----------------------
    ``setuptools`` copies *everything* that lives next to your compiled
    extension into *build_lib*, and later the wheel builder zips up that entire
    directory.  If your ``.cpp`` files are co‑located with the Python package
    (as they often are in pybind11 projects), they end up in the wheel unless
    explicitly removed.  This subclass deletes them immediately after the
    compiler finishes, guaranteeing a slim, binary‑only wheel.
    """

    #: Glob patterns to delete inside the package directory after build.
    _SOURCE_PATTERNS: tuple[str, ...] = (
        "*.c",
        "*.cc",
        "*.cpp",
        "*.cxx",
        "*.h",
        "*.hpp",
    )

    def run(self) -> None:
        """Compile *ext* and immediately remove the original source files."""
        log.debug("Building extension: %s", log.pretty_repr(self.extensions))
        super().run()

        # Path to the *installed* package inside the build directory.
        build_root = Path(self.build_lib)

        log.debug(
            "Pruning source files from wheel: %s -> %s",
            build_root,
            ", ".join(self._SOURCE_PATTERNS),
        )

        removed: list[str] = []
        for pattern in self._SOURCE_PATTERNS:
            for file in build_root.rglob(pattern):
                try:
                    file.unlink(missing_ok=True)
                    log.debug("Removed source file: %s", file)
                    removed.append(str(file.relative_to(build_root)))
                except FileNotFoundError:
                    continue

        if removed:
            log.debug("Pruned %d source files from wheel: %s", len(removed), ", ".join(removed))
