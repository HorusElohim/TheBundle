import os
import asyncio
import pytest
import rich_click as click

import bundle
from bundle.core import logger, tracer

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def testing():
    pass


@click.group()
@tracer.Sync.decorator.call_raise
async def python():
    pass


@python.command("pytest")
@tracer.Sync.decorator.call_raise
@click.option("--show-exc", is_flag=True, help="Show expected trace Exceptions")
@click.option("--perf", is_flag=True, help="Show expected trace Exceptions")
async def pytest_cmd(show_exc: bool, perf: bool):
    """
    Run pytest directly from this CLI instance using pytest.main().
    This runs the tests in a separate thread.
    """
    # Avoid show tracer expected exception
    if not show_exc:
        bundle.core.tracer.DEFAULT_LOG_EXC_LEVEL = logger.Level.EXPECTED_EXCEPTION

    # Avoid logger overhead
    if perf:
        os.environ["PERFORMANCE"] = "true"

    bundle_folder = bundle.Path(list(bundle.__path__)[0])
    tests_folder = bundle_folder.parent.parent / "tests"
    log.debug("bundle_folder=%s, tests_folder=%s", str(bundle_folder), tests_folder)

    # Run pytest.main() in a separate thread so that its event loop
    # creation and teardown is isolated from the current (running) loop.
    test_result = await asyncio.to_thread(pytest.main, [str(tests_folder)])

    if test_result == 0:
        log.info("Test success")
    else:
        log.error("Test failed")


testing.add_command(python)
