# Copyright 2024 HorusElohim

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
from typing import Type
from bundle.core import Process, ProcessStream, ProcessError

SUCCESS_COMMANDS = [
    "echo validcommand",
]
FAILING_COMMANDS = [
    "invalidcommand",  # Command does not exist
]

# List of process classes to test
PROCESS_CLASSES = [Process, ProcessStream]
PROCESS_CLASS_TYPE = Type[Process] | Type[ProcessStream]


# Mark all tests in this module as asynchronous
pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
@pytest.mark.parametrize("command", SUCCESS_COMMANDS)
@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)  # 5ms + ~3ms
async def test_process_success(process_class: PROCESS_CLASS_TYPE, command, request):
    process = process_class(name="Success")
    process_return = await process(command)
    process_return.__test_name = request.node.name.strip()
    return process_return


@pytest.mark.parametrize("process_class", PROCESS_CLASSES)
@pytest.mark.parametrize("command", FAILING_COMMANDS)
@pytest.mark.bundle_data()
@pytest.mark.bundle_cprofile(expected_duration=5_000_000, performance_threshold=3_000_000)  # 5ms + ~3ms
async def test_process_failure(process_class, command, request):
    process = process_class(name="ExpectedFail")
    with pytest.raises(ProcessError) as exc_info:
        await process(command)
    process_error_result = exc_info.value
    process_error_result.result.__test_name = request.node.name.strip()
    return process_error_result.result
