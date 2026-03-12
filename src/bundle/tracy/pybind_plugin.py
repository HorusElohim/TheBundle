# Copyright 2025 HorusElohim
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

"""PybindPluginSpec that injects Tracy-specific, platform-conditional build flags."""

import sys

from bundle.pybind.plugins import PybindPluginSpec
from bundle.pybind.specs import ModuleSpec


class TracyPlatformPlugin(PybindPluginSpec):
    async def apply(self, module: ModuleSpec) -> ModuleSpec:
        if sys.platform == "win32":
            module.extra_compile_args.extend(["/DTRACY_ENABLE", "/EHsc"])
        else:
            module.extra_compile_args.append("-DTRACY_ENABLE")
            module.extra_link_args.extend(["-lpthread", "-ldl"])
        return module
