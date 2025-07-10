from __future__ import annotations

from .. import data
from .base import PlatformSpecificBase
from .command import CommandProcess, CommandList


class WindowsPlatform(PlatformSpecificBase):
    """
    Data model for Windows platform-specific information.
    """

    name: str = "windows"
    os_caption: str = data.Field(default_factory=str, frozen=True)
    os_version: str = data.Field(default_factory=str, frozen=True)
    os_build_number: str = data.Field(default_factory=str, frozen=True)
    computer_model: str = data.Field(default_factory=str, frozen=True)
    bios_serial_number: str = data.Field(default_factory=str, frozen=True)
    cpu_name: str = data.Field(default_factory=str, frozen=True)

    @classmethod
    def command_list(cls) -> CommandList:
        """
        Return the set of commands to gather Windows-specific fields.
        """
        return CommandList(
            commands=[
                CommandProcess(name="os_caption", command="wmic os get Caption /value"),
                CommandProcess(name="os_version", command="wmic os get Version /value"),
                CommandProcess(name="os_build_number", command="wmic os get BuildNumber /value"),
                CommandProcess(name="computer_model", command="wmic computersystem get Model /value"),
                CommandProcess(name="bios_serial_number", command="wmic bios get SerialNumber /value"),
                CommandProcess(name="cpu_name", command="wmic cpu get Name /value"),
            ]
        )
