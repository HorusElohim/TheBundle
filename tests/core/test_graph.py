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


import pytest
import bundle
from bundle import testing

bundle.tests.LOGGER.debug("TASK_TESTS")

GRAPH_CLASSES_TO_TEST = [
    testing.TestGraph.Sync,
    testing.TestGraph.Async,
]


@pytest.mark.parametrize("graph", GRAPH_CLASSES_TO_TEST)
def test_graph_initialization(graph: type(bundle.Graph.Base), tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def graph_initialization_default():
        return graph()

    graph_initialization_default()


ROOT_NODE_TO_TEST = testing.TestGraph.TestNodeSync(
    name="RootNode",
    children=[
        testing.TestGraph.TestNodeSync(
            name="ChildNode1",
            children=[
                testing.TestGraph.TestNodeSync(name="ChildNode1Child1"),
                testing.TestGraph.TestNodeAsync(
                    name="ChildNode1Child2",
                    children=[
                        testing.TestGraph.TestNodeSync(name="ChildNode1Child2Child1"),
                        testing.TestGraph.TestNodeAsync(name="ChildNode1Child2Child2"),
                    ],
                ),
            ],
        ),
        testing.TestGraph.TestNodeAsync(
            name="ChildNode2",
            children=[
                testing.TestGraph.TestNodeSync(name="ChildNode2Child1"),
                testing.TestGraph.TestNodeAsync(
                    name="ChildNode2Child2",
                    children=[
                        testing.TestGraph.TestNodeSync(name="ChildNode1Child1Child1"),
                        testing.TestGraph.TestNodeAsync(name="ChildNode1Child2Child2"),
                    ],
                ),
            ],
        ),
    ],
)


@pytest.mark.parametrize(
    "graph",
    [
        testing.TestGraph.Sync(name="GraphTask", root=ROOT_NODE_TO_TEST),
        testing.TestGraph.Async(name="GraphAsyncTask", root=ROOT_NODE_TO_TEST),
    ],
)
def test_graph_execution(cprofile_folder, reference_folder, graph: bundle.Graph.Base):
    @bundle.tests.graph_decorator(reference_folder, cprofile_folder)
    def graph_execution():
        return graph

    graph_execution()
