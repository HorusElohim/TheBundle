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
@click.option("--show-exc", is_flag=True, default=False, help="Show expected trace Exceptions")
@click.option("--no-logs", is_flag=True, default=False, help="Set log to FATAL avoiding log overhead")
@click.option("--no-cprof", is_flag=True, default=False, help="Disable cprofile")
@click.option("-s", "--capture", is_flag=True, default=False, help="Capture stdout")
async def pytest_cmd(show_exc: bool, no_logs: bool, no_cprof: bool, capture: bool):
    """
    Run the bundle test suite.
    """
    # Avoid show tracer expected exception
    if not show_exc:
        bundle.core.tracer.DEFAULT_LOG_EXC_LEVEL = logger.Level.EXPECTED_EXCEPTION

    # Avoid logger overhead
    if no_logs:
        log.info("disable logs")
        os.environ["NO_LOGS"] = "true"

    if no_cprof:
        log.info("disable cprofile")
        bundle.testing.decorators.set_cprofile_enabled(False)

    bundle_folder = bundle.Path(list(bundle.__path__)[0])
    tests_folder = bundle_folder.parent.parent / "tests"
    log.info("bundle_folder=%s, tests_folder=%s", str(bundle_folder), tests_folder)

    cmd = [str(tests_folder)]
    if capture:
        log.info("enable capture stdout")
        cmd += ["-s"]

    # Run pytest.main() in a separate thread so that its event loop
    # creation and teardown is isolated from the current (running) loop.
    # NB: The thread cannot be interrupted in Python.
    test_result = await asyncio.to_thread(pytest.main, cmd)

    if test_result == 0:
        log.info("Test success")
        exit(0)
    else:
        log.error("Test failed")
        exit(1)


testing.add_command(python)
