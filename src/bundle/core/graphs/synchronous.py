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

import asyncio
from typing import Any
from .. import data, tasks, nodes
from . import LOGGER, GraphABC


@data.dataclass(unsafe_hash=True)
class GraphTask(GraphABC, tasks.Task):
    @classmethod
    def run_node(cls, node: nodes.NodeABC, *args, **kwds) -> dict[str, Any]:
        assert isinstance(node, nodes.NodeABC)
        LOGGER.debug(f"run node: {node.tag}")

        results = {}

        match node:
            case nodes.NodeSyncABC():
                node_output = cls.run_sync_node(node, *args, **kwds)
            case nodes.NodeAsyncABC():
                node_output = asyncio.run(cls.run_async_node(node, *args, **kwds))
            case nodes.NodeABC():
                LOGGER.warn(f"running NodeABC node: {node.tag}")
                node_output = None
            case _ as unsupported_type:
                raise TypeError(f"Unsupported type for root_node: {unsupported_type}")

        results[node.tag] = node_output

        LOGGER.debug(f"running children for node: {node.tag}")
        for child_node in node.children:
            results[child_node.tag] = GraphTask.run_node(child_node, node_output)

        return results

    def exec(self, *args, **kwds):
        return GraphTask.run_node(self.root, *args, **kwds)
