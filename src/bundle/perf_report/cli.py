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

"""
bundle perf_report CLI

  bundle perf_report generate --backend cprofile -i <input> -o <output>
  bundle perf_report generate --backend tracy -i <input> -o <output>
"""

from pathlib import Path

import rich_click as click

from bundle.core import logger, tracer

log = logger.get_logger(__name__)


@click.group()
@tracer.Sync.decorator.call_raise
async def perf_report():
    """Performance report generation."""
    pass


@perf_report.command()
@click.option(
    "--input-path",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Directory with profile data (.prof or .csv)",
)
@click.option("--output-dir", "-o", required=True, type=click.Path(), help="Output directory")
@click.option("--h5/--no-h5", default=True, help="Save HDF5 data alongside PDF")
@click.option("--pdf-name", default=None, help="PDF filename (auto-generated if omitted)")
@click.option(
    "--backend",
    type=click.Choice(["cprofile", "tracy", "auto"]),
    default="auto",
    help="Profiler backend (auto-detects from input files)",
)
@tracer.Sync.decorator.call_raise
async def generate(input_path, output_dir, h5, pdf_name, backend):
    """Generate a performance report with auto-comparison."""
    from bundle import version as bundle_version
    from bundle.perf_report.report.base import get_platform_id, safe_key

    inp = Path(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if backend == "auto":
        backend = _detect_backend(inp)
        log.info("Auto-detected backend: %s", backend)

    pid = get_platform_id()
    if pdf_name is None:
        pdf_name = f"perf_report_{safe_key(bundle_version)}_{safe_key(pid)}.pdf"

    pdf_path = out / pdf_name
    h5_path = out / "profiles.h5" if h5 else None

    if backend == "tracy":
        from bundle.perf_report.report.tracy import generate_report
    else:
        from bundle.perf_report.report.cprofile import generate_report

    await generate_report(inp, pdf_path, h5_path)

    if pdf_path.exists():
        log.info("Report saved to %s", pdf_path)
    else:
        log.warning("No report generated — check input data at %s", inp)


def _detect_backend(input_path: Path) -> str:
    """Auto-detect backend from file types in the input path."""
    if input_path.is_file():
        if input_path.suffix in (".csv", ".tracy"):
            return "tracy"
        return "cprofile"
    has_prof = any(input_path.rglob("*.prof"))
    has_tracy = any(input_path.glob("*.csv")) or any(input_path.glob("*.tracy"))
    if has_prof and not has_tracy:
        return "cprofile"
    if has_tracy and not has_prof:
        return "tracy"
    return "cprofile"
