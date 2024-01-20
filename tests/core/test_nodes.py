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
from bundle.testing import TestNode

bundle.tests.LOGGER.debug("TASK_NODES")

NODES_CLASSES_TO_TEST = [
    TestNode.Sync,
    TestNode.Async,
    TestNode.Process,
    TestNode.ProcessAsync,
    TestNode.StreamingProcess,
    TestNode.StreamingProcessAsync,
]


@pytest.mark.parametrize("node", NODES_CLASSES_TO_TEST)
def test_node_initialization(node, tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def node_initialization_default():
        return node()

    node_initialization_default()


@pytest.mark.parametrize(
    "node, result",
    [
        (TestNode.Sync(name="Node"), "Node"),
        (TestNode.Async(name="NodeAsyncTask"), "NodeAsyncTask"),
    ],
)
def test_node_task_execution(cprofile_folder, node, result):
    @bundle.tests.task_decorator(expected_result=result, cprofile_dump_dir=cprofile_folder)
    def node_task_execution():
        return node

    node_task_execution()


@pytest.mark.parametrize(
    "node, expected_stdout, expected_stderr",
    [
        (TestNode.Process(command='printf "Test"'), "Test", ""),
        (TestNode.ProcessAsync(command="printf AsyncTest"), "AsyncTest", ""),
        (TestNode.StreamingProcess(command="printf StreamingTest"), "StreamingTest", ""),
        (TestNode.StreamingProcessAsync(command="printf StreamingAsyncTest"), "StreamingAsyncTest", ""),
    ],
)
def test_process_execution(cprofile_folder, node, expected_stdout, expected_stderr):
    @bundle.tests.process_decorator(
        expected_stdout=expected_stdout,
        expected_stderr=expected_stderr,
        cprofile_dump_dir=cprofile_folder,
    )
    def node_process_execution():
        return node

    node_process_execution()
