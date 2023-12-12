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

from typing import Any
from .. import data, tasks, nodes
from . import LOGGER, GraphBase


@data.dataclass(unsafe_hash=True)
class GraphAsyncTask(GraphBase, tasks.AsyncTask):
    @classmethod
    async def run_node(cls, node: nodes.NodeBase, *args, **kwds) -> dict[str, Any]:
        assert isinstance(node, nodes.NodeBase)
        LOGGER.debug(f"run node: {node.tag}")
        results = {}

        match node:
            case nodes.Node.Base():
                node_output = cls.run_sync_node(node, *args, **kwds)
            case nodes.Node.Async.Base():
                node_output = await cls.run_async_node(node, *args, **kwds)
            case nodes.NodeBase():
                LOGGER.warn(f"running NodeBase node: {node.tag}")
                node_output = None
            case _ as unsupported_type:
                raise TypeError(f"Unsupported type for root_node: {unsupported_type}")

        results[node.tag] = node_output

        LOGGER.debug(f"running children for node: {node.tag}")
        for child_node in node.children:
            results[child_node.tag] = await GraphAsyncTask.run_node(child_node, node_output)

        return results

    async def exec(self, *args, **kwds):
        return await GraphAsyncTask.run_node(self.root, *args, **kwds)
