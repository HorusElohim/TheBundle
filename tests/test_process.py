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
from bundle.testing import TestProcess

bundle.tests.LOGGER.debug("PROCESS_TESTS")


PROCESS_CLASSES_TO_TEST = [
    TestProcess.Sync,
    TestProcess.Async,
    TestProcess.Streaming,
    TestProcess.StreamingAsync,
]


@pytest.mark.parametrize("process_class", PROCESS_CLASSES_TO_TEST)
def test_process_initialization(reference_folder, cprofile_folder, process_class, tmp_path: bundle.Path):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def process_initialization_default():
        return process_class()

    process_initialization_default()


@pytest.mark.parametrize(
    "process_class, expected_stdout, expected_stderr",
    [
        (TestProcess.Sync(command='printf "Test"'), "Test", ""),
        (TestProcess.Async(command="printf AsyncTest"), "AsyncTest", ""),
        (TestProcess.Streaming(command="printf StreamingTest"), "StreamingTest", ""),
        (TestProcess.StreamingAsync(command="printf StreamingAsyncTest"), "StreamingAsyncTest", ""),
    ],
)
def test_process_execution(cprofile_folder, process_class, expected_stdout, expected_stderr):
    @bundle.tests.process_decorator(
        expected_stdout=expected_stdout,
        expected_stderr=expected_stderr,
        cprofile_dump_dir=cprofile_folder,
    )
    def process_execution():
        return process_class

    process_execution()
