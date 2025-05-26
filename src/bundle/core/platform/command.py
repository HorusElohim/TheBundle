from __future__ import annotations

from typing import Callable, Awaitable, Callable, Union

from .. import data, tracer, logger
from .base import CommandBase, CommandList
from ..process import Process, ProcessError

log = logger.get_logger(__name__)


class CommandProcess(CommandBase):
    """
    Represents a single platform-specific shell command and its result.

    Attributes:
        name (str): The identifier for the command.
        command (str): The shell command to execute.
        result (str): The output/result of the executed command.
    """

    command: str

    async def run(self):
        """
        Execute the shell command asynchronously and store its output in `result`.

        Returns:
            None

        Raises:
            ProcessError: If the command execution fails.
        """
        proc = Process(name=f"ProcessCommand.{self.name}")
        try:
            result = await proc(self.command)
            self.result = result.stdout.strip().strip('"')
        except ProcessError:
            log.error("Command '%s' failed to execute: %s", self.name, self.command)


class CommandCallable(CommandBase):
    """
    Represents a single platform-specific shell command and its result.

    Attributes:
        name (str): The identifier for the command.
        command (str): The shell command to execute.
        result (str): The output/result of the executed command.
        func (Callable[[], Awaitable[str]]): An async function returning the result.
    """

    func: Callable[[], object | data.Data] = data.Field(
        default=lambda: "", description="Sync function that returns the command output"
    )

    @tracer.Async.decorator.call_raise
    async def run(self) -> None:
        """
        Execute the shell command asynchronously and store its output in `result`.

        Raises:
            Exception: Any error from `func` is re-raised after logging.
        """
        try:
            self.result = await tracer.Async.call_raise(self.func)
        except Exception as e:
            log.error("Callable '%s' failed to execute: %s", self.name, e)
            raise
