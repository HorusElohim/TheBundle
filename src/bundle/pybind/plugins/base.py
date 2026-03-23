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

"""Defines PybindPlugin (ABC)"""

from abc import ABC, abstractmethod

from ..resolved import ModuleResolved
from ..specs import ModuleSpec


class PybindPluginSpec(ABC):
    @abstractmethod
    async def apply(self, module: ModuleSpec) -> ModuleSpec:
        """
        Applies plugin logic to a module specification or a resolved module.
        This method is asynchronous to allow for I/O operations within plugins.
        It should return the (potentially modified) module. For immutability,
        it's recommended to return a new instance if changes are made.
        """
        raise NotImplementedError("Plugin 'apply' method must be implemented by subclasses.")


class PybindPluginResolved(ABC):
    @abstractmethod
    async def apply(self, module: ModuleResolved) -> ModuleResolved:
        """
        Applies plugin logic to a resolved module.
        This method is asynchronous to allow for I/O operations within plugins.
        It should return the (potentially modified) module. For immutability,
        it's recommended to return a new instance if changes are made.
        """
        raise NotImplementedError("Plugin 'apply' method must be implemented by subclasses.")
