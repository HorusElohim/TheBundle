# Copyright 2023 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import abc
from typing import Any
from . import LOGGER
from .. import data, entity, nodes


@data.dataclass(unsafe_hash=True)
class GraphBase(entity.Entity):
    root: nodes.NodeBase = data.field(default_factory=nodes.NodeBase)

    @classmethod
    def run_sync_node(cls, node: nodes.Node.Sync, *args, **kwargs):
        LOGGER.debug(f"run node sync: {node.tag}")
        return node(*args, **kwargs)

    @classmethod
    async def run_async_node(cls, node: nodes.Node.Async, *args, **kwargs):
        LOGGER.debug(f"run node async: {node.tag}")
        return await node(*args, **kwargs)

    @abc.abstractclassmethod
    def run_node(cls, node: nodes.NodeBase) -> dict[str, Any]:
        pass
