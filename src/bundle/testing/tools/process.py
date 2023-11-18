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


import logging
import subprocess
from pathlib import Path
from functools import wraps
import asyncio

from ... import data, process
from . import cprofile_decorator, assert_instance_identity, assert_compare

LOGGER = logging.getLogger(__name__)


@data.dataclass
class TestProcess(process.Process):
    born_time: int = 1
    
    def exec(self, **kwds) -> bool:
        kwds["capture_output"] = True
        kwds["text"] = True
        return super().exec(**kwds)


@data.dataclass
class TestAsyncProcess(process.AsyncProcess):
    born_time: int = 1


@data.dataclass
class TestStreamingProcess(process.StreamingProcess):
    born_time: int = 1


@data.dataclass
class TestStreamingAsyncProcess(process.StreamingAsyncProcess):
    born_time: int = 1


def process_decorator(
    expected_stdout: str = None,
    expected_stderr: str = None,
    cprofile_dump_dir: Path | None = None,
):
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwds):
            proc = test_func(*args, **kwds)
            LOGGER.debug(f"testing {proc=}")

            assert_instance_identity(proc, process.Process | process.AsyncProcess)

            @cprofile_decorator(cprofile_dump_dir=cprofile_dump_dir)
            async def process_execution_async():
                await proc()
                return proc

            @cprofile_decorator(cprofile_dump_dir=cprofile_dump_dir)
            def process_execution_sync():
                proc()
                return proc

            # Execute process and assert based on process type
            if isinstance(proc, process.AsyncProcess):
                executed_process = asyncio.run(process_execution_async())
            else:
                executed_process = process_execution_sync()

            # Check stdout and stderr
            assert_compare(expected_stdout, executed_process.stdout)
            assert_compare(expected_stderr, executed_process.stderr)

        return wrapper

    return decorator
