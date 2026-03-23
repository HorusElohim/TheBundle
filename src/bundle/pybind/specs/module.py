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
    include_dirs: list[str] = data.Field(default_factory=list)
    extra_compile_args: list[str] = data.Field(default_factory=list)
    extra_link_args: list[str] = data.Field(default_factory=list)
