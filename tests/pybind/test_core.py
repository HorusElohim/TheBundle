# Copyright 2024 HorusElohim
# Licensed under the Apache License, Version 2.0

import pytest
from pathlib import Path
from setuptools import Extension

from bundle.pybind.core import PybindModule
from bundle.pybind.config import ModuleConfig
import bundle.pybind.core as core_mod


def test_to_extension_basic(tmp_path):
    cfg = ModuleConfig(name="m", sources=["src/a.cpp"], cpp_std="17")
    module = PybindModule(cfg)
    ext = module.to_extension(tmp_path)
    assert isinstance(ext, Extension)
    assert ext.name == "m"
    # Check C++ std flag included
    assert any("-std=c++17" in arg for arg in ext.extra_compile_args)
    # Source path resolved
    assert str((tmp_path / "src/a.cpp").resolve()) in ext.sources


def test_to_extension_with_pkgconfig(monkeypatch, tmp_path):
    """
    Monkey-patch run_pkg_config_cached so that to_extension
    incorporates pkg-config flags into the Extension.
    """
    # Clear cache in case run_pkg_config_cached was previously called
    core_mod.run_pkg_config_cached.cache_clear()

    def fake_run(pkgs, dirs):
        return (["inc"], ["-O3"], ["ld"], ["foo"], ["-Wl"])

    # Patch the function on the core module
    monkeypatch.setattr(core_mod, "run_pkg_config_cached", fake_run)

    cfg = ModuleConfig(
        name="m",
        sources=["a.cpp"],
        pkg_config_packages=["p"],
        pkg_config_dirs=["d"],
        extra_compile_args=[],
    )
    module = PybindModule(cfg)
    ext = module.to_extension(tmp_path)

    assert "inc" in ext.include_dirs
    assert "-O3" in ext.extra_compile_args
    assert "ld" in ext.library_dirs
    assert "foo" in ext.libraries
    assert "-Wl" in ext.extra_link_args
