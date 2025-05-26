from __future__ import annotations

import os
import platform as _platform
import sys
from pathlib import Path

from .. import data, entity
from .base import PlatformBase
from .command import CommandCallable, CommandList
from .darwin import DarwinPlatform
from .windows import WindowsPlatform


class Platform(PlatformBase, entity.Entity):
    """
    Represents the current platform's system and Python environment information.
    """

    name: str = data.Field(default="Host", frozen=True)
    system: str = data.Field(default_factory=str, frozen=True)
    node: str = data.Field(default_factory=str, frozen=True)
    release: str = data.Field(default_factory=str, frozen=True)
    platform_version: str = data.Field(default_factory=str, frozen=True)
    arch: str = data.Field(default_factory=str, frozen=True)
    processor: str = data.Field(default_factory=str, frozen=True)
    python_version: str = data.Field(default_factory=str, frozen=True)
    python_implementation: str = data.Field(default_factory=str, frozen=True)
    python_executable: str = data.Field(default_factory=str, frozen=True)
    python_compiler: str = data.Field(default_factory=str, frozen=True)
    cwd: str = data.Field(default_factory=str, frozen=True)
    home: str = data.Field(default_factory=str, frozen=True)
    env: str = data.Field(default_factory=str, frozen=True)
    is_64bits: str = data.Field(default_factory=str, frozen=True)
    pid: str = data.Field(default_factory=str, frozen=True)
    uid: str = data.Field(default_factory=str, frozen=True)
    gid: str = data.Field(default_factory=str, frozen=True)

    darwin: DarwinPlatform | None = data.Field(default=None, frozen=True)
    windows: WindowsPlatform | None = data.Field(default=None, frozen=True)

    _expected_missing_fields = set(entity.Entity.model_fields)

    @classmethod
    def command_list(cls) -> CommandList:
        return CommandList(
            commands=[
                CommandCallable(name="system", func=lambda: _platform.system().lower()),
                CommandCallable(name="node", func=lambda: _platform.node()),
                CommandCallable(name="release", func=lambda: _platform.release()),
                CommandCallable(name="platform_version", func=lambda: _platform.version()),
                CommandCallable(name="arch", func=lambda: _platform.machine()),
                CommandCallable(
                    name="processor", func=lambda: _platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "")
                ),
                CommandCallable(name="python_version", func=lambda: _platform.python_version()),
                CommandCallable(name="python_implementation", func=lambda: _platform.python_implementation()),
                CommandCallable(name="python_executable", func=lambda: sys.executable),
                CommandCallable(name="python_compiler", func=lambda: _platform.python_compiler()),
                CommandCallable(name="cwd", func=lambda: str(Path.cwd())),
                CommandCallable(name="home", func=lambda: str(Path.home())),
                CommandCallable(name="env", func=lambda: str(dict(os.environ))),
                CommandCallable(name="is_64bits", func=lambda: str(sys.maxsize > 2**32)),
                CommandCallable(name="pid", func=lambda: str(os.getpid())),
                CommandCallable(name="uid", func=lambda: str(os.getuid()) if hasattr(os, "getuid") else ""),
                CommandCallable(name="gid", func=lambda: str(os.getgid()) if hasattr(os, "getgid") else ""),
                CommandCallable(name="darwin", func=DarwinPlatform.run),
                CommandCallable(name="windows", func=WindowsPlatform.run),
            ]
        )

    @property
    def platform_string(self) -> str:
        """
        Returns a string like "darwin-x86_64-cpython3.10.0".
        """
        return f"{self.system}-{self.arch}-{self.python_implementation}{self.python_version}"

    @property
    def is_windows(self) -> bool:
        return self.system == "windows"

    @property
    def is_linux(self) -> bool:
        return self.system == "linux"

    @property
    def is_darwin(self) -> bool:
        return self.system == "darwin"


# Singleton instance constructed at import
platform_info = Platform.run()
