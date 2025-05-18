# Copyright 2024 HorusElohim
# Licensed under the Apache License, Version 2.0

import pytest
from setuptools import Extension

from bundle.pybind.config import ModuleConfig
from bundle.pybind.core import PybindModule
from bundle.pybind.pkgconfig import PkgConfig


pytestmark = pytest.mark.asyncio


async def test_to_extension_basic(tmp_path):
    cfg = ModuleConfig(name="m", sources=["src/a.cpp"], cpp_std="17")
    module = PybindModule(cfg)
    ext = await module.to_extension(tmp_path)
    assert isinstance(ext, Extension)
    assert ext.name == "m"
    # Check C++ std flag included
    assert any("-std=c++17" in arg for arg in ext.extra_compile_args)
    # Source path resolved
    assert str((tmp_path / "src/a.cpp").resolve()) in ext.sources


async def test_to_extension_with_pkgconfig(monkeypatch, tmp_path):
    """
    Monkey-patch PkgConfig.run so that to_extension
    incorporates pkg-config flags into the Extension.
    """

    async def fake_run(pkgs, dirs) -> PkgConfig.Config:
        return PkgConfig.Config(
            include_dirs=["inc"],
            compile_flags=["-O3"],
            library_dirs=["ld"],
            libraries=["foo"],
            link_flags=["-Wl"],
        )

    # Patch the function on the PkgConfig class
    monkeypatch.setattr(PkgConfig, "run", fake_run)

    cfg = ModuleConfig(
        name="m",
        sources=["a.cpp"],
        pkg_config_packages=["p"],
        pkg_config_dirs=["d"],
        extra_compile_args=[],
    )
    module = PybindModule(cfg)
    ext = await module.to_extension(tmp_path)

    assert "inc" in ext.include_dirs
    assert "-O3" in ext.extra_compile_args
    assert "ld" in ext.library_dirs
    assert "foo" in ext.libraries
    assert "-Wl" in ext.extra_link_args
