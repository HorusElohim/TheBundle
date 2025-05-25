"""
pybind.py

Primary CLI entrypoint for loading, resolving, and building pybind11 bindings via
setup.py or direct build calls. Delegates extension creation and custom build_ext
behavior to extension.py.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
from pathlib import Path

import toml
from setuptools import setup as setuptools_setup

from bundle.core import logger, process, tracer

from .extension import ExtensionBuild, ExtensionSpec
from .plugins import PybindPluginResolved, PybindPluginSpec
from .resolved import ProjectResolved
from .resolvers import ProjectResolver
from .specs import ProjectSpec

log = logger.get_logger(__name__)


class Pybind:
    """
    Orchestrates reading pyproject.toml, applying plugins, resolving module specs,
    and constructing Extension objects via extension.make_extension.
    """

    def __init__(
        self,
        pyproject_path: Path | str,
        plugins: list[object] | None = None,
    ) -> None:
        self.pyproject = Path(pyproject_path)
        self.base_dir = self.pyproject.parent
        self.spec = self._load_project_spec()
        self.resolver = ProjectResolver()
        self.resolved: ProjectResolved | None = None
        self.plugins: list[object] = plugins or []

    @tracer.Sync.decorator.call_raise
    def _load_project_spec(self) -> ProjectSpec:
        if not self.pyproject.exists():
            raise FileNotFoundError(f"{self.pyproject} does not exist")
        data = toml.load(self.pyproject)
        cfg = data.get("tool", {}).get("pybind11")
        if cfg is None:
            raise KeyError("Missing [tool.pybind11] in pyproject.toml")
        log.debug("Loaded spec: %s", cfg)
        return ProjectSpec(**cfg)

    @tracer.Sync.decorator.call_raise
    def register_plugin(self, plugin: object) -> None:
        self.plugins.append(plugin)

    async def _apply_plugins(
        self,
        modules: list,
        plugin_type: type,
    ) -> None:
        tasks: list = []
        for plugin in self.plugins:
            if isinstance(plugin, plugin_type):
                log.debug("Applying plugin %s", plugin)
                tasks.extend(plugin.apply(m) for m in modules)
        if tasks:
            await asyncio.gather(*tasks)

    @tracer.Async.decorator.call_raise
    async def apply_spec_plugins(self) -> None:
        """
        Run all PybindPluginSpec instances against raw module specs.
        """
        await self._apply_plugins(self.spec.modules, PybindPluginSpec)

    @tracer.Async.decorator.call_raise
    async def apply_resolved_plugins(self) -> None:
        """
        Run all PybindPluginResolved instances against resolved modules.
        """
        if not self.resolved:
            raise ValueError("Must resolve before applying resolved plugins")
        await self._apply_plugins(self.resolved.modules, PybindPluginResolved)

    @tracer.Async.decorator.call_raise
    async def resolve(self) -> ProjectResolved:
        await self._apply_plugins(self.spec.modules, PybindPluginSpec)
        self.resolved = await self.resolver.resolve(self.spec)
        await self._apply_plugins(self.resolved.modules, PybindPluginResolved)
        return self.resolved

    @tracer.Async.decorator.call_raise
    async def get_spec_extensions(self) -> list[ExtensionBuild]:
        """
        Resolve the project and build all Extension objects concurrently.
        """
        resolved = await self.resolve()
        tasks = [ExtensionSpec.from_module_resolved(m) for m in resolved.modules]
        return list(await asyncio.gather(*tasks))

    @classmethod
    @tracer.Sync.decorator.call_raise
    def setup(
        cls,
        invoking_file: Path | str,
        **kwargs,
    ) -> None:
        """
        Entry point for setup.py: build Extension list and invoke setuptools.setup.
        """
        root = Path(invoking_file).parent.resolve()
        pyproject = root / "pyproject.toml"
        pyb = cls(pyproject, plugins=kwargs.pop("plugins", []))

        exts = asyncio.run(pyb.get_spec_extensions())
        kwargs.setdefault("ext_modules", []).extend(exts)
        kwargs.setdefault("cmdclass", {})["build_ext"] = ExtensionBuild
        setuptools_setup(**kwargs)

    @classmethod
    @tracer.Async.decorator.call_raise
    async def build(
        cls,
        path: str,
        parallel: int = multiprocessing.cpu_count(),
    ):
        """
        Shell out to `python setup.py build_ext` with optional parallel.
        """
        module_path = Path(path).resolve()
        cmd = f"python {module_path/'setup.py'} build_ext"
        if parallel:
            cmd += f" --parallel {parallel}"

        env = os.environ.copy()
        proc = process.Process(name="Pybind.build")
        return await proc(cmd, cwd=str(module_path), env=env)

    @classmethod
    @tracer.Async.decorator.call_raise
    async def info(cls, path: str):
        """
        Load and resolve project for inspection without building.
        """
        pyproject = Path(path).resolve() / "pyproject.toml"
        pyb = cls(pyproject)
        resolved = await pyb.resolve()
        log.info(await resolved.as_json())
        return resolved
