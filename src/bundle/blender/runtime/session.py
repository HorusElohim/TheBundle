"""Session orchestration for launching Blender subprocesses."""

from __future__ import annotations

import shlex
from typing import Sequence

from bundle.core import data, logger, process

log = logger.get_logger(__name__)


class BlenderLaunchRequest(data.Data):
    """Parameters describing how to launch Blender."""

    executable: str
    args: Sequence[str] = ()
    env: dict[str, str] | None = None

    def as_command(self) -> str:
        """Return the shell command string to execute via bundle.core.process."""
        parts = [str(self.executable), *[str(arg) for arg in self.args]]
        return shlex.join(parts)


class BlenderSession:
    """Wrapper around `bundle.core.process.Process` to execute Blender runs."""

    def __init__(self, launch_request: BlenderLaunchRequest) -> None:
        self.launch_request = launch_request
        self._process = process.Process()

    async def run(self) -> process.ProcessResult:
        """Execute Blender with the configured arguments."""
        command = self.launch_request.as_command()
        log.debug("Launching Blender with command: %s", command)
        return await self._process(command, env=self.launch_request.env)
