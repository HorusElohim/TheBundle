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

# extension.py

"""
extension.py

Provides:
- `make_extension`: an async helper to turn a ModuleResolved into a setuptools.Extension
- `BuildExtension`: custom build_ext command for per-extension temp dirs on non-Windows
  and safe in-place copying on Windows.
"""

from __future__ import annotations

from setuptools import Extension
from setuptools.command.build_ext import build_ext as ExtensionBuild

from bundle.core import logger, platform_info, tracer

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
