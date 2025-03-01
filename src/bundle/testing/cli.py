import pytest
import rich_click as click

import bundle
from bundle.core import data, logger, process, tracer

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def testing():
    pass


@click.group()
@tracer.Sync.decorator.call_raise
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
@tracer.Sync.decorator.call_raise
@click.option("--show-exc", is_flag=True, help="Show expected trace Exceptions")
async def pytest_cmd(show_exc: bool):
    """
    Run pytest directly from this CLI instance using pytest.main().
    This runs the tests in a separate thread.
    """
    # Lower the logger level to show all messages during testing.
    bundle.BUNDLE_LOGGER.setLevel(logger.Level.VERBOSE)

    # Avoid show tracer expected exception
    if not show_exc:
        bundle.core.tracer.DEFAULT_LOG_EXC_LEVEL = logger.Level.EXPECTED_EXCEPTION

    bundle_folder = bundle.Path(list(bundle.__path__)[0])
    tests_folder = bundle_folder.parent.parent / "tests"
    log.debug("bundle_folder=%s, tests_folder=%s", str(bundle_folder), tests_folder)

    def run_pytest():
        import nest_asyncio

        nest_asyncio.apply()
        return tracer.Sync.call_raise(pytest.main, [str(tests_folder)])

    run_pytest()

    log.info("All tests passed successfully.")


testing.add_command(python)
