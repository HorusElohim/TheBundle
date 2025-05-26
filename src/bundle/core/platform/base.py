from __future__ import annotations

import abc
import asyncio
import platform as _platform
from typing import ClassVar

from .. import data, tracer, logger

log = logger.get_logger(__name__)


class CommandBase(data.Data):
    """
    Represents a single platform-specific shell command and its result.

    Attributes:
        name (str): The identifier for the command.
        command (str): The shell command to execute.
        result (str): The output/result of the executed command.
    """

    name: str
    result: str = data.Field(default_factory=str)

    async def run(self):
        """
        Execute the shell command asynchronously and store its output in `result`.
        """
        raise NotImplementedError("Subclasses must implement the run method.")


class CommandList(data.Data):
    """
    Represents a collection of platform-specific commands to be executed.

    Attributes:
        commands (list[ProcessCommand]): List of ProcessCommand instances.
    """

    commands: list[CommandBase] = data.Field(default_factory=list)

    @tracer.Sync.decorator.call_raise
    async def run(self) -> CommandList:
        """
        Execute all contained platform commands asynchronously.

        Returns:
            CommandList: The instance with updated results for each command.
        """
        if not self.commands:
            return {}
        tasks = [cmd.run() for cmd in self.commands]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self


class PlatformBase(data.Data):
    """
    Abstract base class for platform-specific data models.
    """

    name: str = data.Field(default_factory=str, frozen=True)
    _expected_missing_fields: ClassVar[set[str]] = {"name"}

    @classmethod
    @abc.abstractmethod
    def command_list(cls) -> CommandList | None:
        """
        Return the set of commands required to gather platform-specific information.
        """
        raise NotImplementedError("Subclasses must implement command_list method.")

    @classmethod
    def _sanity_check(cls, command_list: CommandList) -> None:
        """
        Perform a sanity check on the command list to ensure all commands are valid.

        Raises:
            ValueError: If any command is not an instance of CommandBase.
        """
        defined_commands = {cmf.name for cmf in command_list.commands}
        class_model_fields = set(cls.model_fields) - cls._expected_missing_fields

        if defined_commands == class_model_fields:
            return
        if defined_commands < class_model_fields:
            missing = class_model_fields - defined_commands
            log.warning("Missing commands for model fields: %s in class %s", missing, cls.__name__)
        else:
            extra = defined_commands - class_model_fields
            log.warning("Commands not defined in model fields: %s in class", extra, cls.__name__)

    @classmethod
    def should_run(cls) -> bool:
        """
        Determine if the platform-specific commands should be run based on the system type.

        Returns:
            bool: True if the platform-specific commands should be run, False otherwise.
        """
        return _platform.system().lower() == cls.system.lower()

    @classmethod
    @tracer.Sync.decorator.call_raise
    def run(cls) -> PlatformBase | None:
        """
        Resolve and instantiate the platform-specific data model by running its commands.

        Returns:
            PlatformSpecific: An instance populated with command results.
        """
        command_list = cls.command_list()

        if command_list is None:
            log.warning("No command list defined for platform %s", cls.__name__)
            return None

        if not isinstance(command_list, CommandList):
            raise ValueError(f"Expected CommandList, got {type(command_list).__name__} for {cls.__name__}")

        cls._sanity_check(command_list)

        tracer.Sync.call_raise(command_list.run)
        for cmd in command_list.commands:
            if not isinstance(cmd, CommandBase):
                raise ValueError(f"Command {cmd.name} is not an instance of CommandBase")
        return cls(**{cmd.name: cmd.result for cmd in command_list.commands})


class PlatformSpecificBase(PlatformBase):
    @classmethod
    def should_run(cls) -> bool:
        """
        Determine if the platform-specific commands should be run based on the system type.

        Returns:
            bool: True if the platform-specific commands should be run, False otherwise.
        """
        platform_specific = cls()
        return _platform.system().lower() == platform_specific.name

    @classmethod
    @tracer.Sync.decorator.call_raise
    def run(cls) -> PlatformSpecificBase:
        """
        Resolve and instantiate the platform-specific data model by running its commands.

        Returns:
            PlatformSpecific: An instance populated with command results.
        """
        if not cls.should_run():
            log.debug("Platform-specific commands should not run for %s", cls.__name__)
            return None

        return super().run()
