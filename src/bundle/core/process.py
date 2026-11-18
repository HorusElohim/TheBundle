# Copyright 2026 HorusElohim

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

from __future__ import annotations

import asyncio
import shlex
import sys
from collections.abc import Sequence
from os import PathLike, fspath
from typing import Any

from . import logger, tracer
from .data import Data, PrivateAttr
from .entity import Entity

log = logger.get_logger(__name__)
Command = str | Sequence[str | PathLike[str]]


def parse_args(command: Command) -> tuple[str, ...]:
    """Normalize literal arguments without splitting or rewriting shell strings."""
    arguments = (command,) if isinstance(command, str) else tuple(fspath(argument) for argument in command)
    if not arguments:
        raise ValueError("Expected a nonempty argument sequence")
    if any(not isinstance(argument, str) for argument in arguments):
        raise TypeError("Arguments must be strings or text paths")
    return arguments


class ProcessResult(Data):
    """Data class to store the result of a process execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str


class ProcessError(Exception):
    """Custom exception for process execution errors."""

    def __init__(self, process: Process, result: ProcessResult):
        self.result = result
        parts = [
            f"\n\n{'--' * 10} Process Execution Error {'--' * 10}\n",
            log.pretty_repr(process),
            f"\n\n\t{'--' * 10} Standard Output {'--' * 10}\n",
            result.stdout.replace("\r\n", "\n").strip(),
            f"\n\n\t{'--' * 10} Error Output {'--' * 10}\n",
            result.stderr.replace("\r\n", "\n").strip(),
            f"\n\n{'--' * 10} End of Process Execution Error {'--' * 10}\n",
        ]
        super().__init__("\n".join(parts))


class Process(Entity):
    """Capture output from a shell string or a literal argument sequence."""

    _process: asyncio.subprocess.Process | None = PrivateAttr(default=None)

    @tracer.Async.decorator.call_raise
    async def __call__(self, command: Command, **kwargs) -> ProcessResult:
        """
        Execute asynchronously and capture output. Strings use a shell;
        argument sequences execute directly, without shell expansion.

        Args:
            command: A shell string or a nonempty sequence of executable/arguments.
            **kwargs: Additional keyword arguments for subprocess.

        Returns:
            ProcessResult: Contains return code, stdout, and stderr.

        Raises:
            ProcessError: If the command execution fails.
            OSError: If an argument-vector executable cannot be started.
        """
        return await self._internal_call_(command, **kwargs)

    async def _start_process(self, command: Command, **kwargs) -> asyncio.subprocess.Process:
        arguments = parse_args(command)
        options: dict[str, Any] = dict(stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **kwargs)
        if isinstance(command, str):
            return await tracer.Async.call_raise(asyncio.create_subprocess_shell, arguments[0], **options)
        return await tracer.Async.call_raise(asyncio.create_subprocess_exec, *arguments, **options)

    async def _internal_call_(self, command: Command, **kwargs) -> ProcessResult:
        self._process = await self._start_process(command, **kwargs)
        stdout, stderr = await self._process.communicate()
        return self._result(command, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"))

    def _result(self, command: Command, stdout: str, stderr: str) -> ProcessResult:
        assert self._process is not None
        result = ProcessResult(
            command=command if isinstance(command, str) else shlex.join(parse_args(command)),
            returncode=-1 if self._process.returncode is None else self._process.returncode,
            stdout=stdout,
            stderr=stderr,
        )
        if result.returncode != 0:
            raise ProcessError(self, result)
        return result


class ProcessStream(Process):
    """Executes a command asynchronously and streams output line by line."""

    @tracer.Async.decorator.call_raise
    async def __call__(self, command: Command, **kwargs) -> ProcessResult:
        """
        Execute a shell string or literal arguments and stream output line by line.

        Args:
            command: A shell string or a nonempty sequence of executable/arguments.
            **kwargs: Additional keyword arguments for subprocess.

        Returns:
            ProcessResult: Contains return code, accumulated stdout, and stderr.

        Raises:
            ProcessError: If the command execution fails.
            OSError: If an argument-vector executable cannot be started.
        """
        stdout_lines = []
        stderr_lines = []

        return await self._internal_call_(
            command,
            stdout_lines,
            stderr_lines,
            **kwargs,
            log_level=logger.Level.VERBOSE,
        )

    async def _internal_call_(self, command: Command, stdout_lines: list, stderr_lines: list, **kwargs) -> ProcessResult:  # type: ignore
        self._process = await self._start_process(command, **kwargs)

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
        return self._result(command, "".join(stdout_lines), "".join(stderr_lines))

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
                str_line = line.decode("utf-8", errors="replace")
                accumulator.append(str_line)
                await handler(str_line)
        except Exception as e:
            log.error(f"Exception while reading stream: {e}")

    async def callback_stdout(self, line: str):
        """Default stdout handler: writes directly to sys.stdout."""
        sys.stdout.write(line)
        sys.stdout.flush()

    async def callback_stderr(self, line: str):
        """Default stderr handler: writes directly to sys.stderr."""
        sys.stderr.write(line)
        sys.stderr.flush()
