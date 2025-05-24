from __future__ import annotations

import asyncio
import multiprocessing
import os
from pathlib import Path

import toml
from setuptools import Extension
from setuptools import setup as setuptools_setup

from bundle.core import logger, process, tracer, platform_info

from .resolved.project import ProjectResolved
from .resolvers.project import ProjectResolver
from .specs.project import ProjectSpec
from .plugins import PybindPluginSpec, PybindPluginResolved

log = logger.get_logger(__name__)


class Pybind:
    """
    Main orchestrator for loading, resolving, and building pybind11 extension modules.
    """

    def __init__(self, pyproject_path: str | Path, plugins: list = None):
        self.pyproject_path = Path(pyproject_path)
        self.project_spec = self._load_project_spec()
        self.base_dir = self.pyproject_path.parent
        self.resolver = ProjectResolver()
        self.project_resolved: ProjectResolved | None = None
        self._plugins: list = plugins or []

    @tracer.Sync.decorator.call_raise
    def _load_project_spec(self) -> ProjectSpec:
        log.debug(f"Loading pyproject.toml from {self.pyproject_path}")
        if not self.pyproject_path.exists():
            raise FileNotFoundError(f"{self.pyproject_path} does not exist")
        raw = toml.load(self.pyproject_path)
        section = raw.get("tool", {}).get("pybind11")
        if section is None:
            raise KeyError("Missing [tool.pybind11] in pyproject.toml")
        print(f"Loaded pyproject.toml: {section}")
        return ProjectSpec(**section)

    @tracer.Sync.decorator.call_raise
    def register_plugin(self, plugin) -> None:
        self._plugins.append(plugin)

    @tracer.Async.decorator.call_raise
    async def apply_spec_plugins(self) -> None:
        for plugin in self._plugins:
            match plugin:
                case PybindPluginSpec():
                    log.debug(f"Applying Spec plugin: {plugin.__class__.__name__}")
                    tasks = [plugin.apply(module) for module in self.project_spec.modules]
                    await asyncio.gather(*tasks)
                case _:
                    log.warning(f"Unknown plugin type: {plugin.__class__.__name__}")

    @tracer.Async.decorator.call_raise
    async def apply_resolved_plugins(self) -> None:
        if not self.project_resolved:
            raise ValueError("Project must be resolved before applying resolved plugins")
        for plugin in self._plugins:
            match plugin:
                case PybindPluginResolved():
                    log.debug(f"Applying Resolved plugin: {plugin.__class__.__name__}")
                    tasks = [plugin.apply(module) for module in self.project_resolved.modules]
                    await asyncio.gather(*tasks)
                case _:
                    log.warning(f"Unknown plugin type: {plugin.__class__.__name__}")

    def get_module_names(self) -> list[str]:
        return [m.name for m in self.project_spec.modules]

    def get_module_specs(self):
        return self.project_spec.modules

    @tracer.Async.decorator.call_raise
    async def resolve(self) -> ProjectResolved:
        await self.apply_spec_plugins()
        self.project_resolved = await self.resolver.resolve(self.project_spec)
        await self.apply_resolved_plugins()
        return self.project_resolved

    @tracer.Async.decorator.call_raise
    async def get_extensions(self) -> list[Extension]:
        log.debug("Getting extensions for all modules")
        await self.resolve()
        import pybind11

        ext_modules = []
        for module in self.project_resolved.modules:
            include_dirs = [pybind11.get_include()]
            libraries = []
            library_dirs = []
            extra_link_args = []
            extra_compile_args = []
            module_spec = module.spec
            std_flag = f"/std:c++{module_spec.cpp_std}" if platform_info.is_windows else f"-std=c++{module_spec.cpp_std}"
            sources = [str(Path(s)) for s in module_spec.sources]
            # Use the single pkgconfig field (PkgConfigResolved)
            pkg = module.pkgconfig
            if pkg:
                for pkg_result in pkg.resolved:
                    libraries.extend(pkg_result.libraries)
                    include_dirs.extend(pkg_result.include_dirs)
                    library_dirs.extend(pkg_result.library_dirs)
                    extra_link_args.extend(pkg_result.link_flags)
                    extra_compile_args.extend(pkg_result.compile_flags)
            if std_flag not in extra_compile_args:
                extra_compile_args.append(std_flag)
            log.debug("Creating Extension for module %s", module_spec.name)
            ext = Extension(
                name=module_spec.name,
                sources=sources,
                language=module_spec.language,
                include_dirs=include_dirs,
                library_dirs=library_dirs,
                libraries=libraries,
                extra_compile_args=extra_compile_args,
                extra_link_args=extra_link_args,
            )
            # custom build_temp to avoid conflicts when building multiple extensions
            ext._build_temp = f"build/temp_{module_spec.name}"
            ext_modules.append(ext)
        return ext_modules

    @classmethod
    @tracer.Sync.decorator.call_raise
    def setup(cls, invoking_file: str | Path, **kwargs):
        project_root = Path(invoking_file).parent.resolve()
        pyproject_file = project_root / "pyproject.toml"
        pybind = cls(pyproject_file)

        for plugin in kwargs.pop("plugins", []):
            pybind.register_plugin(plugin)

        import asyncio

        ext_modules = asyncio.run(pybind.get_extensions())
        kwargs.setdefault("ext_modules", []).extend(ext_modules)

        if "BUILD_PARALLEL" in os.environ:
            try:
                kwargs["parallel"] = int(os.environ["BUILD_PARALLEL"])
            except ValueError:
                pass

        # Custom build_ext to set per-extension build_temp only
        from setuptools.command.build_ext import build_ext as _build_ext

        class build_ext(_build_ext):
            def build_extension(self, ext):
                # Set unique build_temp for each extension if present
                build_temp = getattr(ext, "_build_temp", None)
                if build_temp:
                    self.build_temp = build_temp
                    os.makedirs(self.build_temp, exist_ok=True)
                # Do not set build_lib
                super().build_extension(ext)

        kwargs["cmdclass"] = kwargs.get("cmdclass", {})
        kwargs["cmdclass"]["build_ext"] = build_ext

        setuptools_setup(**kwargs)

    @classmethod
    @tracer.Async.decorator.call_raise
    async def build(cls, path: str, parallel: int = multiprocessing.cpu_count()) -> process.ProcessResult:

        module_path = Path(path).resolve()
        cmd = f"python {module_path / 'setup.py'} build_ext --inplace"
        if parallel and not platform_info.is_windows:
            # Use --parallel only on non-Windows platforms
            cmd += f" --parallel {parallel}"

        log.info(f"Running build command in {module_path}:")

        env = os.environ.copy()

        if platform_info.is_darwin:
            # Set ARCHFLAGS to match the current Python architecture
            env["ARCHFLAGS"] = f"-arch {platform_info.arch}"
            # Set deployment target for bindings build
            env["MACOSX_DEPLOYMENT_TARGET"] = str(platform_info.darwin.macosx_deployment_target)

        proc = process.Process(name="Pybind.build")
        result = await proc(cmd, cwd=str(module_path), env=env)
        log.info(f"Build completed with return code {result.returncode}")
        return result

    @classmethod
    @tracer.Async.decorator.call_raise
    async def info(cls, path: str) -> ProjectResolved:
        module_path = Path(path).resolve()
        toml_file = module_path / "pyproject.toml"
        pybind = cls(toml_file)
        project_resolved = await pybind.resolve()
        json_text = await project_resolved.as_json()
        log.info(f"pybind11 configuration from {toml_file}:\n{json_text}")
        return project_resolved
