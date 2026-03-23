# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from pathlib import Path

import pytest
import toml

from bundle.pybind.pybind import Pybind, PybindPluginResolved, PybindPluginSpec

pytestmark = pytest.mark.asyncio


@pytest.fixture
def minimal_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        toml.dumps(
            {
                "tool": {
                    "pybind11": {
                        "modules": [
                            {
                                "name": "testmod",
                                "sources": ["testmod.cpp"],
                                "language": "c++",
                                "cpp_std": "17",
                                "pkgconfig": {
                                    "packages": [],
                                    "extra_dirs": [],
                                },
                                "extra_compile_args": [],
                                "extra_link_args": [],
                            }
                        ]
                    }
                }
            }
        )
    )
    (tmp_path / "testmod.cpp").write_text("// dummy source\n")
    return pyproject


async def test_from_pyproject_and_module_names(minimal_pyproject):
    pybind = Pybind(minimal_pyproject)
    assert len(pybind.spec.modules) == 1
    assert pybind.spec.modules[0].name == "testmod"


async def test_register_plugin_spec_and_apply(minimal_pyproject):
    pybind = Pybind(minimal_pyproject)
    called = {}

    class DummyPlugin(PybindPluginSpec):
        async def apply(self, module):
            called["applied"] = module.name

    pybind.register_plugin(DummyPlugin())
    await pybind.apply_spec_plugins()
    assert called["applied"] == "testmod"


async def test_register_plugin_resolved_and_apply(minimal_pyproject):
    pybind = Pybind(minimal_pyproject)
    called = {}

    class DummyResolved(PybindPluginResolved):
        async def apply(self, module_resolved):
            called["applied"] = module_resolved.spec.name

    pybind.register_plugin(DummyResolved())
    await pybind.resolve()
    assert called.get("applied") == "testmod"


async def test_get_spec_extensions(minimal_pyproject):
    pybind = Pybind(minimal_pyproject)
    # Patch pybind11.get_include to avoid dependency
    import sys
    import types

    fake_pybind11 = types.ModuleType("pybind11")
    fake_pybind11.get_include = lambda: "/fake/include"
    sys.modules["pybind11"] = fake_pybind11

    exts = await pybind.get_spec_extensions()
    assert len(exts) == 1
    ext = exts[0]
    assert ext.name == "testmod"
    assert "pybind11" in ext.include_dirs[0]
