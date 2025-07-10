from __future__ import annotations

import sysconfig

from .. import data
from .base import PlatformSpecificBase
from .command import CommandProcess, CommandCallable, CommandList


class DarwinPlatform(PlatformSpecificBase):
    """
    Data model for macOS (Darwin) platform-specific information.
    """

    name: str = "darwin"
    product_version: str = data.Field(default_factory=str, frozen=True)
    build_version: str = data.Field(default_factory=str, frozen=True)
    kernel_version: str = data.Field(default_factory=str, frozen=True)
    hardware_model: str = data.Field(default_factory=str, frozen=True)
    hardware_uuid: str = data.Field(default_factory=str, frozen=True)
    xcode_version: str = data.Field(default_factory=str, frozen=True)
    command_line_tools_version: str = data.Field(default_factory=str, frozen=True)
    macosx_deployment_target: float = data.Field(default=0.0, frozen=True)

    @staticmethod
    async def _fetch_deployment_target() -> str:
        val = sysconfig.get_config_var("MACOSX_DEPLOYMENT_TARGET")
        return str(val) if val not in (None, "") else ""

    @classmethod
    def command_list(cls) -> CommandList:
        return CommandList(
            commands=[
                CommandProcess(name="product_version", command="sw_vers -productVersion"),
                CommandProcess(name="build_version", command="sw_vers -buildVersion"),
                CommandProcess(name="kernel_version", command="uname -r"),
                CommandProcess(name="hardware_model", command="sysctl -n hw.model"),
                CommandProcess(
                    name="hardware_uuid",
                    command="ioreg -rd1 -c IOPlatformExpertDevice | awk '/IOPlatformUUID/ { print $3; }'",
                ),
                CommandProcess(name="xcode_version", command="xcodebuild -version 2>/dev/null"),
                CommandProcess(
                    name="command_line_tools_version",
                    command=(
                        "pkgutil --pkg-info=com.apple.pkg.CLTools_Executables 2>/dev/null " "| grep version | awk '{print $2}'"
                    ),
                ),
                CommandCallable(
                    name="macosx_deployment_target",
                    func=DarwinPlatform._fetch_deployment_target,
                ),
            ]
        )
