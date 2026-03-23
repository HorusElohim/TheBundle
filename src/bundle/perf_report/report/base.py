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

"""Shared utilities for performance report generation (cProfile and Tracy)."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

from bundle import version as bundle_version
from bundle.core import logger
from bundle.core.platform import platform_info
from bundle.latex import Document, Figure, Section, Table, escape
from bundle.latex.elements import Column

LOGGER = logger.setup_root_logger(name=__name__)

MAX_PARALLEL_ASYNC = 20
TOP_N_PLOT = 10
TOP_N_TABLE = 30

TIME_THRESHOLDS = [
    (1.0, "s", 1.0),
    (1e-3, "ms", 1e3),
    (1e-6, "\u03bcs", 1e6),
    (0.0, "ns", 1e9),
]

CLR_CURRENT = "#87CEEB"
CLR_BASELINE = "#FF8C66"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def format_time_seconds(seconds: float) -> tuple[str, str]:
    """Format a seconds value into a human-readable (value, unit) pair."""
    if seconds == 0:
        return "0", "ns"
    abs_val = abs(seconds)
    for threshold, unit, multiplier in TIME_THRESHOLDS:
        if abs_val >= threshold:
            scaled = seconds * multiplier
            if scaled >= 100:
                return f"{scaled:,.0f}", unit
            elif scaled >= 10:
                return f"{scaled:,.1f}", unit
            else:
                return f"{scaled:,.2f}", unit
    scaled = seconds * 1e9
    return f"{scaled:,.2f}", "ns"


def format_time_ns(nanoseconds: int | float) -> tuple[str, str]:
    """Format a nanosecond value into a human-readable (value, unit) pair."""
    return format_time_seconds(nanoseconds / 1e9)


def format_delta(current: int | float, baseline: int | float) -> str:
    if baseline == 0:
        return "--"
    pct = ((current - baseline) / baseline) * 100
    if abs(pct) < 0.5:
        return "~0\\%"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.0f}\\%"


def delta_color(current: int | float, baseline: int | float) -> str:
    if baseline == 0:
        return "textcolor"
    pct = ((current - baseline) / baseline) * 100
    if pct < -2:
        return "green"
    elif pct > 2:
        return "red"
    return "textcolor"


def best_unit_for_values_seconds(times_seconds: list[float]) -> tuple[str, float]:
    """Return the best (unit, multiplier_from_seconds) for a list of second values."""
    if not times_seconds:
        return "ns", 1e9
    max_val = (
        max(abs(t) for t in times_seconds if t != 0)
        if any(t != 0 for t in times_seconds)
        else 0
    )
    for threshold, unit, multiplier in TIME_THRESHOLDS:
        if max_val >= threshold:
            return unit, multiplier
    return "ns", 1e9


def best_unit_for_values_ns(times_ns: list[int | float]) -> tuple[str, float]:
    """Return the best (unit, multiplier_from_ns) for a list of nanosecond values."""
    if not times_ns:
        return "ns", 1.0
    max_val_s = (
        max(abs(t) for t in times_ns if t != 0) / 1e9
        if any(t != 0 for t in times_ns)
        else 0
    )
    for threshold, unit, multiplier in TIME_THRESHOLDS:
        if max_val_s >= threshold:
            return unit, multiplier / 1e9
    return "ns", 1.0


def shorten_path(file_path: str, max_parts: int = 2) -> str:
    """Truncate a file path to its last ``max_parts`` segments."""
    file_path = file_path.replace("\\", "/")
    if file_path in ("N/A", "built-in", "~"):
        return file_path
    parts = file_path.split("/")
    if len(parts) <= max_parts:
        return file_path
    return "/".join(parts[-max_parts:])


def normalize_src_path(src_file: str) -> str:
    """Extract bundle-relative path: .../bundle/core/tracer.py -> core/tracer.py"""
    p = src_file.replace("\\", "/")
    marker = "/bundle/"
    idx = p.rfind(marker)
    if idx >= 0:
        return p[idx + len(marker) :]
    return p


def safe_key(v: str) -> str:
    return v.replace("+", "_").replace("/", "_").replace("\\", "_")


def get_platform_id() -> str:
    return f"{platform_info.system}-{platform_info.arch}-{platform_info.python_implementation}{platform_info.python_version}"


def get_platform_meta() -> dict:
    return {
        "system": platform_info.system,
        "arch": platform_info.arch,
        "node": platform_info.node,
        "release": platform_info.release,
        "processor": platform_info.processor,
        "python_version": platform_info.python_version,
        "python_implementation": platform_info.python_implementation,
        "python_compiler": platform_info.python_compiler,
        "is_64bits": str(platform_info.is_64bits),
    }


def truncate_labels(labels: list[str], max_len: int = 50) -> list[str]:
    return [la if len(la) <= max_len else "..." + la[-(max_len - 3) :] for la in labels]


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def setup_plot(
    n_bars: int, has_baseline: bool
) -> tuple[plt.Figure, plt.Axes, np.ndarray]:
    """Create a dark-themed horizontal bar chart canvas."""
    fig_height = max(3, n_bars * (0.7 if has_baseline else 0.5) + 1)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#1E1E1E")
    ax.grid(True, linestyle=":", color="#333333", alpha=0.5, axis="x")
    return fig, ax, np.arange(n_bars)


def draw_baseline_bars(
    ax: plt.Axes, y_pos: np.ndarray, baseline_times: list[float], bar_height: float
):
    """Draw baseline comparison bars and add the legend."""
    ax.barh(
        y_pos + bar_height / 2,
        baseline_times,
        height=bar_height,
        color=CLR_BASELINE,
        edgecolor="#CC7055",
        linewidth=0.5,
        label="Baseline",
    )
    ax.legend(
        loc="lower right",
        fontsize=7,
        facecolor="#2d2d2d",
        edgecolor="#555555",
        labelcolor="#D3D3D3",
    )


def finalize_plot(
    fig: plt.Figure,
    ax: plt.Axes,
    bars: Any,
    max_val: float,
    xlabel: str,
    plot_path: Path,
) -> Path:
    """Apply bar-value labels, axis formatting, and save the plot."""

    def smart_fmt(x, _):
        if max_val >= 1000:
            return f"{x:,.0f}"
        elif max_val >= 10:
            return f"{x:,.1f}"
        return f"{x:,.3f}"

    ax.xaxis.set_major_formatter(FuncFormatter(smart_fmt))
    tick_interval = max_val / 4 if max_val > 0 else 1
    ax.xaxis.set_major_locator(MultipleLocator(tick_interval))
    ax.set_xlim(right=max_val * 1.15)
    ax.set_xlabel(xlabel, color="#D3D3D3", fontsize=9)
    ax.tick_params(axis="x", colors="#D3D3D3", labelsize=8)
    ax.tick_params(axis="y", colors="#D3D3D3", labelsize=7)

    xlim_max = ax.get_xlim()[1]
    for bar in bars:
        width = bar.get_width()
        if max_val >= 1000:
            label = f"{width:,.0f}"
        elif max_val >= 10:
            label = f"{width:,.1f}"
        else:
            label = f"{width:,.3f}"
        if width < xlim_max * 0.3:
            ha, lx, color = "left", width + xlim_max * 0.01, "#D3D3D3"
        else:
            ha, lx, color = "right", width - xlim_max * 0.01, "#1E1E1E"
        ax.text(
            lx,
            bar.get_y() + bar.get_height() / 2,
            label,
            ha=ha,
            va="center",
            color=color,
            weight="bold",
            fontsize=7,
        )

    ax.invert_yaxis()
    for spine in ax.spines.values():
        spine.set_color("#333333")

    fig.savefig(
        plot_path,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0.2,
        dpi=200,
    )
    plt.close(fig)
    LOGGER.info("Plot saved: %s", plot_path)
    return plot_path


# ---------------------------------------------------------------------------
# Section builder
# ---------------------------------------------------------------------------


def build_platform_section(meta: dict) -> Section:
    """Build a platform info summary table from HDF5 metadata."""
    section = Section("Platform Info", level=1)
    columns = [
        Column("Property", width="4cm", align="l"),
        Column("Value", width="10cm", align="l"),
    ]
    table = Table(columns, row_color_alt="rowalt")
    for key, label in [
        ("system", "System"),
        ("arch", "Architecture"),
        ("node", "Hostname"),
        ("release", "OS Release"),
        ("processor", "Processor"),
        ("python_version", "Python Version"),
        ("python_implementation", "Python Impl."),
        ("python_compiler", "Python Compiler"),
        ("is_64bits", "64-bit"),
        ("bundle_version", "Bundle Version"),
    ]:
        val = meta.get(key, "")
        if val:
            table.add_row([escape(label), escape(str(val))])
    section.add_table(table)
    return section


# ---------------------------------------------------------------------------
# Generic report pipeline
# ---------------------------------------------------------------------------


def find_baseline_version(
    storage: Any, current_version: str, platform_id: str
) -> str | None:
    """Find the most recent version in HDF5 that isn't the current one and has this platform."""
    versions = storage.list_versions()
    for version in reversed(versions):
        if version == current_version:
            continue
        if platform_id in storage.list_platforms(version):
            return version
    return None


async def generate_report(
    input_path: Path,
    output_path: Path,
    h5_path: Path | None,
    *,
    extractor_cls: Any,
    storage_cls: Any,
    generate_plot_fn: Callable,
    build_section_fn: Callable,
    build_func_map_fn: Callable,
    file_type_label: str,
):
    """Generic report generation pipeline shared by cProfile and Tracy backends."""
    pid = get_platform_id()
    pmeta = get_platform_meta()

    LOGGER.info("Extracting profiles from %s", input_path)
    profiles = await asyncio.to_thread(extractor_cls.extract_all, input_path)
    if not profiles:
        LOGGER.warning("No %s files found at %s", file_type_label, input_path)
        return

    LOGGER.info("Found %d profiles", len(profiles))
    current_version_key = safe_key(bundle_version)

    if h5_path:
        LOGGER.info(
            "Saving HDF5 to %s (version=%s, platform=%s)", h5_path, bundle_version, pid
        )
        await asyncio.to_thread(
            storage_cls.from_directory,
            input_path,
            h5_path,
            platform_info.node,
            bundle_version,
            pid,
            pmeta,
        )

    baseline_lookup = None
    baseline_meta = None
    if h5_path and h5_path.exists():
        storage = storage_cls(h5_path)
        baseline_version = find_baseline_version(
            storage, current_version_key, safe_key(pid)
        )
        if baseline_version:
            LOGGER.info("Found baseline version: %s", baseline_version)
            baseline_profiles = await asyncio.to_thread(
                storage.load_profiles, baseline_version, pid
            )
            baseline_meta = await asyncio.to_thread(
                storage.load_meta, baseline_version, pid
            )
            if baseline_profiles:
                baseline_lookup = build_func_map_fn(baseline_profiles)

    has_comparison = baseline_lookup is not None
    plot_dir = Path(tempfile.mkdtemp(prefix="profiler_plots_"))

    semaphore = asyncio.Semaphore(MAX_PARALLEL_ASYNC)

    async def gen(profile):
        async with semaphore:
            func_map = baseline_lookup.get(profile.name) if baseline_lookup else None
            return profile, await asyncio.to_thread(
                generate_plot_fn, profile, plot_dir, func_map
            )

    results = await asyncio.gather(*[gen(p) for p in profiles])

    LOGGER.info("Building LaTeX document ...")
    title = f"Performance Report: {escape(bundle_version)}"
    if has_comparison:
        base_ver = (
            baseline_meta.get("bundle_version", "baseline")
            if baseline_meta
            else "baseline"
        )
        title = (
            f"Performance Report: {escape(bundle_version)} vs {escape(str(base_ver))}"
        )

    doc = Document(title=title)
    if has_comparison:
        doc.add_preamble("\\definecolor{green}{HTML}{66BB6A}\n")
        doc.add_preamble("\\definecolor{red}{HTML}{EF5350}\n")

    doc.add_section(build_platform_section({**pmeta, "bundle_version": bundle_version}))
    for profile, plot_path in results:
        func_map = baseline_lookup.get(profile.name) if baseline_lookup else None
        doc.add_section(build_section_fn(profile, plot_path, func_map))

    LOGGER.info("Compiling PDF ...")
    await asyncio.to_thread(doc.save_pdf, output_path)
    LOGGER.info("PDF saved to %s", output_path)

    for _, plot_path in results:
        try:
            os.remove(plot_path)
        except OSError:
            pass
