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

import asyncio
from typing import Optional

from . import tracer
from .data import Data, PrivateAttr
from .entity import Entity
from .logger import get_logger

logger = get_logger(__name__)


class ProcessResult(Data):
    """Data class to store the result of a process execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str


class ProcessError(Exception):
    """Custom exception for process execution errors."""

    def __init__(self, result: ProcessResult):
        super().__init__(f"Command failed with result {result}")
        self.result = result


class Process(Entity):
    """Asynchronously executes shell commands and captures their output."""

    _process: Optional[asyncio.subprocess.Process] = PrivateAttr(default=None)

    @tracer.asyn.decorator_call_raise
    async def __call__(self, command: str, **kwargs) -> ProcessResult:
        """
        Executes a shell command asynchronously and captures the output.

        Args:
            command (str): The shell command to execute.
            **kwargs: Additional keyword arguments for subprocess.

        Returns:
            ProcessResult: Contains return code, stdout, and stderr.

        Raises:
            ProcessError: If the command execution fails.
        """
        return await tracer.asyn.call_raise(self._internal_call_, command, **kwargs)

    async def _internal_call_(self, command: str, **kwargs) -> ProcessResult:

        self._process = await tracer.asyn.call_raise(
            asyncio.create_subprocess_shell,
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )

        stdout, stderr = await tracer.asyn.call_raise(
            self._process.communicate,
        )

        returncode = self._process.returncode

        stdout_decoded = stdout.decode("utf-8") if stdout else ""
        stderr_decoded = stderr.decode("utf-8") if stderr else ""

        # Create the ProcessResult before checking the return code
        result = ProcessResult(command=command, returncode=returncode, stdout=stdout_decoded, stderr=stderr_decoded)

        if returncode != 0:
            raise ProcessError(result)

        return result


class ProcessStream(Process):
    """Executes a command asynchronously and streams output line by line."""

    @tracer.asyn.decorator_call_raise
    async def __call__(self, command: str, **kwargs) -> ProcessResult:
        """
        Executes the command and streams output line by line.

        Args:
            command (str): The shell command to execute.
            **kwargs: Additional keyword arguments for subprocess.

        Returns:
            ProcessResult: Contains return code, accumulated stdout, and stderr.

        Raises:
            ProcessError: If the command execution fails.
        """
        stdout_lines = []
        stderr_lines = []

        return await tracer.asyn.call_raise(self._internal_call_, command, stdout_lines, stderr_lines, **kwargs)

    async def _internal_call_(self, command: str, stdout_lines: list, stderr_lines: list, **kwargs) -> ProcessResult:
        self._process = await tracer.asyn.call_raise(
            asyncio.create_subprocess_shell,
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs,
        )

        assert self._process
        assert self._process.stdout
        assert self._process.stderr

        # Create tasks for reading stdout and stderr streams
        tasks = [
            self._read_stream(self._process.stdout, self.callback_stdout, stdout_lines),
            self._read_stream(self._process.stderr, self.callback_stderr, stderr_lines),
        ]

        # Wait for the process to complete and streams to be read
        await asyncio.gather(*tasks)
        await self._process.wait()

        assert self._process.returncode is not None

        returncode = self._process.returncode

        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        result = ProcessResult(command=command, returncode=returncode, stdout=stdout, stderr=stderr)

        if returncode != 0:
            raise ProcessError(result)

        return result

    async def _read_stream(self, stream: asyncio.StreamReader, handler, accumulator):
        """
        Reads a stream line by line and passes each line to the handler.

        Args:
            stream (asyncio.StreamReader): The stream to read from.
            handler (callable): The handler function to process each line.
            accumulator (list): The accumulator list to collect output lines.
        """
        try:
            async for line in stream:
                str_line = line.decode("utf-8")
                accumulator.append(str_line)
                await tracer.asyn.call_raise(handler, str_line)
        except Exception as e:
            logger.error(f"Exception while reading stream: {e}")

    async def callback_stdout(self, line: str):
        """
        Processes a line from stdout.

        Override this method to customize stdout line handling.
        """
        # Default implementation: log the stdout line
        logger.verbose("STDOUT: %s", line.strip())

    async def callback_stderr(self, line: str):
        """
        Processes a line from stderr.

        Override this method to customize stderr line handling.
        """
        # Default implementation: log the stderr line
        logger.error("STDERR: %s", line.strip())