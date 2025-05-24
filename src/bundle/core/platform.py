from __future__ import annotations

import os
import platform
import sysconfig
import sys
import asyncio

from pathlib import Path
from . import data, tracer
from .entity import Entity
from .process import Process, ProcessError


class ProcessCommand(data.Data):
    """
    Represents a single platform-specific shell command and its result.

    Attributes:
        name (str): The identifier for the command.
        command (str): The shell command to execute.
        result (str): The output/result of the executed command.
    """

    name: str
    command: str
    result: str = data.Field(default_factory=str)

    @tracer.Async.decorator.call_raise
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
            pass


class ProcessCommands(data.Data):
    """
    Represents a collection of platform-specific commands to be executed.

    Attributes:
        commands (list[ProcessCommand]): List of ProcessCommand instances.
    """

    commands: list[ProcessCommand] = data.Field(default_factory=list)

    @tracer.Sync.decorator.call_raise
    async def run(self) -> ProcessCommands:
        """
        Execute all contained platform commands asynchronously.

        Returns:
            ProcessCommands: The instance with updated results for each command.
        """
        if not self.commands:
            return {}
        tasks = [cmd.run() for cmd in self.commands]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self


class PlatformSpecific(data.Data):
    """
    Abstract base class for platform-specific data models.

    Attributes:
        target (str): The platform target identifier (e.g., 'darwin', 'linux').
    """

    target: str = data.Field(default="", frozen=True)

    @classmethod
    def platform_commands(cls) -> ProcessCommands:
        """
        Return a ProcessCommands instance with platform-specific commands.

        Returns:
            ProcessCommands: The commands to be executed for this platform.

        Raises:
            NotImplementedError: If not implemented by a subclass.
        """
        raise NotImplementedError("Subclasses must implement platform_commands method.")

    @classmethod
    def resolve(cls) -> PlatformSpecific:
        """
        Resolve and instantiate the platform-specific data model by running its commands.

        Returns:
            PlatformSpecific: An instance populated with command results.
        """
        if platform.system().lower() != cls.__name__.lower():
            return cls()
        platform_cmds = cls.platform_commands().run()
        return cls(**{cmd.name: cmd.result for cmd in platform_cmds.commands if cmd.result})


class Darwin(PlatformSpecific):
    """
    Data model for macOS (Darwin) platform-specific information.

    Attributes:
        product_version (str): macOS product version.
        build_version (str): macOS build version.
        kernel_version (str): Kernel version.
        hardware_model (str): Hardware model identifier.
        hardware_uuid (str): Hardware UUID.
        xcode_version (str): Xcode version installed.
        command_line_tools_version (str): Command Line Tools version.
    """

    product_version: str = data.Field(default_factory=str, frozen=True)
    build_version: str = data.Field(default_factory=str, frozen=True)
    kernel_version: str = data.Field(default_factory=str, frozen=True)
    hardware_model: str = data.Field(default_factory=str, frozen=True)
    hardware_uuid: str = data.Field(default_factory=str, frozen=True)
    xcode_version: str = data.Field(default_factory=str, frozen=True)
    command_line_tools_version: str = data.Field(default_factory=str, frozen=True)
    macosx_deployment_target: float = data.Field(
        default_factory=lambda: (
            float(val) if (val := sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET")) not in (None, "") else -1.0
        ),
        frozen=True,
    )

    @classmethod
    def platform_commands(cls) -> Darwin:
        """
        Return the set of commands required to gather Darwin/macOS-specific information.

        Returns:
            ProcessCommands: The commands to be executed for Darwin.
        """
        return ProcessCommands(
            commands=[
                ProcessCommand(name="product_version", command="sw_vers -productVersion"),
                ProcessCommand(name="build_version", command="sw_vers -buildVersion"),
                ProcessCommand(name="kernel_version", command="uname -r"),
                ProcessCommand(name="hardware_model", command="sysctl -n hw.model"),
                ProcessCommand(
                    name="hardware_uuid", command="ioreg -rd1 -c IOPlatformExpertDevice | awk '/IOPlatformUUID/ { print $3; }'"
                ),
                ProcessCommand(name="xcode_version", command="xcodebuild -version 2>/dev/null"),
                ProcessCommand(
                    name="command_line_tools_version",
                    command="pkgutil --pkg-info=com.apple.pkg.CLTools_Executables 2>/dev/null | grep version | awk '{print $2}'",
                ),
            ]
        )


class Platform(Entity):
    """
    Represents the current platform's system and Python environment information.

    Attributes:
        system (str): The operating system name (lowercase).
        node (str): The network name (hostname) of the machine.
        release (str): The system's release version.
        version (str): The system's version.
        arch (str): The machine architecture.
        processor (str): The processor identifier.
        python_version (str): The Python version in use.
        python_implementation (str): The Python implementation (e.g., CPython).
        python_executable (str): The path to the Python executable.
        python_compiler (str): The Python compiler used.
        cwd (Path): The current working directory.
        home (Path): The user's home directory.
        env (dict): The environment variables.
        is_64bits (bool): Whether the Python interpreter is 64-bit.
        pid (int): The current process ID.
        uid (int | None): The current user ID (if available).
        gid (int | None): The current group ID (if available).
        darwin (Darwin | None): Darwin-specific platform information (if on macOS).
    """

    system: str = data.Field(default=platform.system().lower(), frozen=True)
    node: str = data.Field(default=platform.node(), frozen=True)
    release: str = data.Field(default=platform.release(), frozen=True)
    version: str = data.Field(default=platform.version(), frozen=True)
    arch: str = data.Field(default=platform.machine(), frozen=True)
    processor: str = data.Field(default=platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", ""), frozen=True)
    python_version: str = data.Field(default=platform.python_version(), frozen=True)
    python_implementation: str = data.Field(default=platform.python_implementation(), frozen=True)
    python_executable: str = data.Field(default=sys.executable, frozen=True)
    python_compiler: str = data.Field(default=platform.python_compiler(), frozen=True)
    cwd: Path = data.Field(default=Path.cwd(), frozen=True)
    home: Path = data.Field(default=Path.home(), frozen=True)
    env: dict = data.Field(default_factory=lambda: dict(os.environ), frozen=True)
    is_64bits: bool = data.Field(default=sys.maxsize > 2**32, frozen=True)
    pid: int = data.Field(default=os.getpid(), frozen=True)
    uid: None | int = data.Field(default=(os.getuid() if hasattr(os, "getuid") else None), frozen=True)
    gid: None | int = data.Field(default=(os.getgid() if hasattr(os, "getgid") else None), frozen=True)

    # Platform-specific attributes
    darwin: None | Darwin = data.Field(default_factory=Darwin.resolve, frozen=True)

    @property
    def platform_string(self) -> str:
        """
        Return a string summarizing the platform and Python environment.

        Returns:
            str: A string in the format "{system}-{machine}-{python_implementation}{python_version}".
        """
        return f"{self.system}-{self.machine}-{self.python_implementation}{self.python_version}"

    @property
    def is_windows(self) -> bool:
        """
        Check if the current system is Windows.

        Returns:
            bool: True if Windows, False otherwise.
        """
        return self.system == "windows"

    @property
    def is_linux(self) -> bool:
        """
        Check if the current system is Linux.

        Returns:
            bool: True if Linux, False otherwise.
        """
        return self.system == "linux"

    @property
    def is_darwin(self) -> bool:
        """
        Check if the current system is Darwin (macOS).

        Returns:
            bool: True if Darwin, False otherwise.
        """
        return self.system == "darwin"


# Singleton instance constructed at import
platform_info = Platform(name="CurrentPlatform")
