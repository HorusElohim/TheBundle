import asyncio

import pytest
import rich_click as click

import bundle
from bundle.core import data, logger, process, tracer

log = logger.get_logger(__name__)


@click.group()
@tracer.syn.decorator_call
async def testing():
    pass


@click.group()
@tracer.syn.decorator_call
async def python():
    pass


class TestProcess(process.Process):
    complete_logs: list[str] = data.Field(default_factory=list)

    async def callback_stdout(self, line: str):
        line = line.strip()
        self.complete_logs.append(line)
        if "PASSED" in line or "====" in line or "SKIPPED" in line:
            log.info("%s", line)

    async def callback_stderr(self, line: str):
        line = line.strip()
        self.complete_logs.append(line)


@python.command("pytest")
@tracer.syn.decorator_call
async def pytest_cmd():
    """
    Run pytest directly from this CLI instance using pytest.main().
    This runs the tests in a separate thread.
    """
    # Lower the logger level to show all messages during testing.
    bundle.BUNDLE_LOGGER.setLevel(logger.Level.NOTSET)

    bundle_folder = bundle.Path(bundle.__path__[0])
    tests_folder = bundle_folder.parent.parent / "tests"
    log.debug("bundle_folder=%s, tests_folder=%s", str(bundle_folder), tests_folder)

    async def run_pytest():
        import nest_asyncio

        nest_asyncio.apply()
        return tracer.syn.call_raise(pytest.main, [str(tests_folder)])

    await run_pytest()

    log.info("All tests passed successfully.")


testing.add_command(python)
