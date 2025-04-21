import pytest
from pathlib import Path
import toml

from bundle.pybind import ModuleConfig, PybindConfig


def test_module_config_defaults(tmp_path):
    # Create minimal config dict
    cfg_dict = {
        "name": "mod.test",
        "sources": ["a.cpp", "b.cpp"],
    }
    mod = ModuleConfig(**cfg_dict)
    assert mod.name == "mod.test"
    assert mod.sources == ["a.cpp", "b.cpp"]
    # Defaults
    assert mod.language == "c++"
    assert mod.cpp_std == "20"
    assert mod.extra_compile_args == []
    assert mod.pkg_config_packages == []


def test_load_toml(tmp_path):
    # Create pyproject.toml
    content = {"tool": {"pybind11": {"modules": [{"name": "x", "sources": ["s.cpp"]}]}}}
    (tmp_path / "pyproject.toml").write_text(toml.dumps(content))
    cfg = PybindConfig.load_toml(tmp_path / "pyproject.toml")
    assert isinstance(cfg, PybindConfig)
    assert len(cfg.modules) == 1
    assert cfg.modules[0].name == "x"
    assert cfg.modules[0].sources == ["s.cpp"]
