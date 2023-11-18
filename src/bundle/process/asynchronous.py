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


import subprocess
import asyncio

from ._abc import ProcessABC, StreamingProcessABC

from . import tasks
from . import data
from . import LOGGER


@data.dataclass
class AsyncProcess(ProcessABC, tasks.AsyncTask):
    async def exec(self, **kwds) -> bool:
        LOGGER.debug(f"running {self.command} asynchronously")

        if "text" in kwds:
            LOGGER.warning("removing 'text' argument because not supported in async proc.")
            del kwds["text"]
        # Asynchronous subprocess execution
        process = await asyncio.create_subprocess_shell(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwds)

        stdout, stderr = await process.communicate()

        self.returncode = process.returncode
        self.stdout = stdout.decode() if stdout else ""
        self.stderr = stderr.decode() if stderr else ""

        self._reset_process()

        if self.returncode == 0:
            LOGGER.debug("ran ✅")
            return True
        else:
            LOGGER.error(f"ran ❌: {self.stderr}")
            return False

    async def terminate(self):
        if self._process is not None:
            try:
                self._process.terminate()
                await self._process.wait()
            except Exception as e:
                LOGGER.error(f"Error terminating process: {e}")


@data.dataclass
class StreamingAsyncProcess(StreamingProcessABC, AsyncProcess):
    async def exec(self, **kwds) -> int:
        self._process = await asyncio.create_subprocess_shell(
            self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwds
        )

        async def read_stdout_stream(stream, callback):
            while True:
                line = await stream.readline()
                if line:
                    line = line.decode()
                    self.stdout += line
                    if callback:
                        callback(line)
                else:
                    break

        async def read_stderr_stream(stream, callback):
            while True:
                line = await stream.readline()
                if line:
                    line = line.decode()
                    self.stderr += line
                    if callback:
                        callback(line)
                else:
                    break

        # Create tasks for reading stdout and stderr
        tasks = [
            read_stdout_stream(self._process.stdout, self.stdout_callback),
            read_stderr_stream(self._process.stderr, self.stderr_callback),
        ]

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Wait for the process to exit and set the return code
        await self._process.wait()

        self._reset_process()

        if self.returncode == 0:
            LOGGER.debug("ran ✅")
            return True
        else:
            LOGGER.error(f"ran ❌: {self.stderr}")
            return False
