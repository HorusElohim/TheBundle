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
from bundle.testing import TestTask

bundle.tests.LOGGER.debug("TASK_TESTS")

TASK_CLASSES_TO_TEST = [
    TestTask.Sync,
    TestTask.Async,
]


@pytest.mark.parametrize("task", TASK_CLASSES_TO_TEST)
def test_task_initialization(task, tmp_path, reference_folder, cprofile_folder):
    @bundle.tests.json_decorator(tmp_path, reference_folder)
    @bundle.tests.data_decorator()
    @bundle.tests.cprofile_decorator(cprofile_dump_dir=cprofile_folder)
    def task_initialization_default():
        return task()

    task_initialization_default()


@pytest.mark.parametrize(
    "task, result",
    [
        (TestTask.Sync(name="Task"), "Task"),
        (TestTask.Async(name="AsyncTask"), "AsyncTask"),
    ],
)
def test_task_execution(cprofile_folder, task, result):
    @bundle.tests.task_decorator(expected_result=result, cprofile_dump_dir=cprofile_folder)
    def task_execution():
        return task

    task_execution()
