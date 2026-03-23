# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import asyncio
import os
import shutil
import sys

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
@click.option(
    "--show-exc", is_flag=True, default=False, help="Show expected trace Exceptions"
)
@click.option(
    "--no-logs",
    is_flag=True,
    default=False,
    help="Set log to FATAL avoiding log overhead",
)
@click.option("-s", "--capture", is_flag=True, default=False, help="Capture stdout")
@click.option(
    "--perf",
    is_flag=True,
    default=False,
    help="Profile with cProfile and generate .prof files",
)
@click.option(
    "--report",
    is_flag=True,
    default=False,
    help="Generate PDF perf report (implies --perf)",
)
@click.option(
    "--tracy",
    is_flag=True,
    default=False,
    help="Profile with Tracy for real-time viewing (alternative to --perf)",
)
@click.option(
    "--perf-output",
    default=None,
    type=click.Path(),
    help="Output directory for perf data (default: <repo>/performances)",
)
async def pytest_cmd(
    show_exc: bool,
    no_logs: bool,
    capture: bool,
    perf: bool,
    report: bool,
    tracy: bool,
    perf_output: str | None,
):
    """
    Run the bundle test suite.
    """
    if not show_exc:
        bundle.core.tracer.DEFAULT_LOG_EXC_LEVEL = logger.Level.EXPECTED_EXCEPTION

    if no_logs:
        log.info("disable logs")
        os.environ["NO_LOGS"] = "true"

    bundle_folder = bundle.Path(next(iter(bundle.__path__)))
    tests_folder = bundle_folder.parent.parent / "tests"
    log.info("bundle_folder=%s, tests_folder=%s", str(bundle_folder), tests_folder)

    extra_args = ["-s"] if capture else []

    if report:
        perf = True

    if tracy:
        await _run_tracy(tests_folder, extra_args, perf_output, report)
    elif perf:
        await _run_cprofile(tests_folder, extra_args, perf_output, report)
    else:
        test_result = await asyncio.to_thread(
            pytest.main, [str(tests_folder), *extra_args]
        )
        if test_result == 0:
            log.info("Test success")
            exit(0)
        else:
            log.error("Test failed")
            exit(1)


async def _run_cprofile(
    tests_folder: bundle.Path,
    extra_args: list[str],
    perf_output: str | None,
    report: bool = False,
) -> None:
    """Pipeline: pytest with CPROFILE_MODE → collect .prof files → (optional) PDF report."""
    from bundle import version as bundle_version
    from bundle.core.platform import platform_info

    perf_dir = (
        bundle.Path(perf_output)
        if perf_output
        else tests_folder.parent / "performances"
    )
    perf_dir.mkdir(parents=True, exist_ok=True)

    # Run pytest as subprocess with cProfile enabled
    env = {**os.environ, "CPROFILE_MODE": "true"}
    log.info("Running pytest with CPROFILE_MODE=true ...")
    pytest_proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        str(tests_folder),
        *extra_args,
        env=env,
    )
    test_result = await pytest_proc.wait()

    # The .prof files are written to references/<platform>/cprofile/ by the decorator
    ref_folder = tests_folder.parent / "references" / platform_info.system / "cprofile"

    if report and ref_folder.exists():
        from bundle.perf_report.report.cprofile import generate_report

        pid = f"{platform_info.system}-{platform_info.arch}-{platform_info.python_implementation}{platform_info.python_version}"
        safe_ver = bundle_version.replace("+", "_").replace("/", "_").replace("\\", "_")
        safe_pid = pid.replace("+", "_").replace("/", "_").replace("\\", "_")

        pdf_path = perf_dir / f"perf_report_{safe_ver}_{safe_pid}.pdf"
        h5_path = perf_dir / "profiles.h5"
        log.info("Generating cProfile perf report → %s ...", pdf_path)
        await generate_report(ref_folder, pdf_path, h5_path)
        log.info("Perf report saved to %s", pdf_path)

    if test_result == 0:
        log.info("Test success")
        exit(0)
    else:
        log.error("Tests failed (exit %d) — perf data still saved", test_result)
        exit(test_result)


async def _run_tracy(
    tests_folder: bundle.Path,
    extra_args: list[str],
    perf_output: str | None,
    report: bool = False,
) -> None:
    """Full pipeline: tracy-capture → pytest (subprocess) → csvexport → (optional) perf report."""
    from bundle import version as bundle_version
    from bundle.perf_report import ProfileExtractor

    perf_dir = bundle.Path(perf_output) if perf_output else tests_folder.parent / "perf"
    perf_dir.mkdir(parents=True, exist_ok=True)

    tracy_name = f"bundle.{bundle_version}.tracy"
    tracy_path = perf_dir / tracy_name

    # Locate native tools (installed to venv by `bundle tracy build`)
    capture_exe = shutil.which("tracy-capture")
    if not capture_exe:
        log.error("tracy-capture not found on PATH — run: bundle tracy build capture")
        exit(1)

    # Tracy starts listening on port 8086 as soon as _tracy_ext is imported.
    # Shut it down in this (CLI) process so the port is free for the subprocess.
    import bundle.tracy as _tracy

    if _tracy.ENABLED:
        log.info("Releasing Tracy port in CLI process ...")
        _tracy._ext.shutdown()

    log.info("Starting tracy-capture → %s", tracy_path)
    capture_proc = await asyncio.create_subprocess_exec(
        capture_exe, "-o", str(tracy_path), "-f"
    )

    # Give the subprocess time to start Tracy and claim port 8086
    await asyncio.sleep(0.5)

    # Run pytest as a subprocess so Tracy's C library disconnects cleanly on exit
    env = {**os.environ, "PERF_MODE": "true"}
    log.info("Running pytest with PERF_MODE=true ...")
    pytest_proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pytest",
        str(tests_folder),
        *extra_args,
        env=env,
    )
    test_result = await pytest_proc.wait()

    # Wait for tracy-capture to finish writing (it exits when the client disconnects)
    log.info("Waiting for tracy-capture to finish ...")
    try:
        await asyncio.wait_for(capture_proc.wait(), timeout=300)
    except TimeoutError:
        log.warning("tracy-capture did not exit in time — terminating")
        capture_proc.terminate()
        await capture_proc.wait()

    if not tracy_path.exists():
        log.error("Tracy file not found at %s — capture may have failed", tracy_path)
        exit(1)

    # Export CSV and load profile data
    log.info("Exporting %s → CSV ...", tracy_name)
    profile = ProfileExtractor.extract_from_tracy(tracy_path)
    csv_path = tracy_path.with_suffix(".csv")
    log.info("CSV saved to %s (%d zones)", csv_path, len(profile.records))

    # Generate PDF report (only when --report is passed)
    if report:
        from bundle.perf_report.report.tracy import generate_report

        pdf_path = perf_dir / f"bundle.{bundle_version}.pdf"
        h5_path = perf_dir / "profiles.h5"
        log.info("Generating Tracy perf report → %s ...", pdf_path)
        await generate_report(csv_path, pdf_path, h5_path)
        log.info("Perf report saved to %s", pdf_path)

    if test_result == 0:
        log.info("Test success")
        exit(0)
    else:
        log.error("Tests failed (exit %d) — perf data still saved", test_result)
        exit(test_result)


testing.add_command(python)
