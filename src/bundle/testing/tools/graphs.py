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

import json
import logging
from pathlib import Path
from functools import wraps
import asyncio
from typing import Any

from ... import data, graphs
from . import TestNodeTask, TestNodeAsyncTask
from . import cprofile_decorator, assert_instance_identity, assert_compare

LOGGER = logging.getLogger(__name__)


@data.dataclass
class TestGraphTask(graphs.GraphTask):
    born_time: int = 1
    root: TestNodeTask = data.field(default_factory=(TestNodeTask))


@data.dataclass
class TestGraphAsyncTask(graphs.GraphAsyncTask):
    born_time: int = 1
    root: TestNodeTask = data.field(default_factory=(TestNodeTask))


@data.dataclass
class TestGraphNodeTask(TestNodeTask):
    def exec(self, *args, **kwargs):
        parent_node_name = "".join(args) + "->" if len(args) > 0 else ""
        return f"{parent_node_name}{self.name}"


@data.dataclass
class TestGraphNodeAsyncTask(TestNodeAsyncTask):
    async def exec(self, *args, **kwargs):
        parent_node_name = "".join(args) + "->" if len(args) > 0 else ""
        return f"{parent_node_name}{self.name}"


@data.dataclass
class GraphResultTest(data.JSONData):
    results: dict[str:Any] = data.field(default_factory=dict)


def graph_decorator(ref_dir: Path, cprofile_dump_dir: Path | None = None):
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwds):
            graph = test_func(*args, **kwds)
            LOGGER.debug(f"testing graph {graph.__class__.__name__}")

            assert_instance_identity(graph, graphs.GraphABC)

            filename = f"{type(graph).__name__}.expected_result.json"
            ref_json_path = ref_dir / "ref" / filename
            failed_error_path = ref_dir / "failed" / "logs" / filename
            ref_json_path.parent.mkdir(exist_ok=True)
            failed_error_path.parent.mkdir(exist_ok=True, parents=True)

            @cprofile_decorator(cprofile_dump_dir=cprofile_dump_dir)
            async def graph_execution_async():
                return await graph()

            @cprofile_decorator(cprofile_dump_dir=cprofile_dump_dir)
            def graph_execution_sync():
                return graph()

            # Execute graph and fetch results
            if isinstance(graph, graphs.GraphAsyncTask):
                results = asyncio.run(graph_execution_async())
            else:
                results = graph_execution_sync()

            graph_result = GraphResultTest(results=results)

            try:
                # Check and use reference if exist
                if ref_json_path.exists():
                    expected_graph_results = GraphResultTest.from_json(ref_json_path)
                    # Compare results with expected outcomes
                    assert_compare(expected_graph_results, graph_result)
                else:
                    LOGGER.warning(f"no existing reference found: {ref_json_path}")
                    graph_result.dump_json(ref_json_path)
                    LOGGER.info(f"new reference: {ref_json_path}")
            except Exception as ex:
                LOGGER.error(str(ex))
                failed_error_path.open("w").write(str(ex))
                raise ex

            return graph

        return wrapper

    return decorator
