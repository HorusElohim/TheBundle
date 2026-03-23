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

"""Tracy-based performance report: zone statistics with min/max/std distribution."""

from pathlib import Path

from bundle.latex import Figure, Section, Table, escape
from bundle.latex.elements import Column
from bundle.perf_report.extractor import ProfileData, ProfileExtractor, ProfileRecord
from bundle.perf_report.storage import ProfileStorage

from .base import (
    CLR_CURRENT,
    TOP_N_PLOT,
    TOP_N_TABLE,
    best_unit_for_values_ns,
    delta_color,
    draw_baseline_bars,
    finalize_plot,
    format_delta,
    format_time_ns,
)
from .base import generate_report as _generate_report
from .base import normalize_src_path, setup_plot, truncate_labels

# ---------------------------------------------------------------------------
# Tracy-specific helpers
# ---------------------------------------------------------------------------


def format_label(rec: ProfileRecord) -> str:
    if not rec.src_file or rec.src_file in ("N/A", ""):
        return f"built-in  {rec.name}"
    return f"{normalize_src_path(f'{rec.src_file}:{rec.src_line}')}  {rec.name}"


def func_key(rec: ProfileRecord) -> str:
    norm = normalize_src_path(rec.src_file) if rec.src_file else rec.src_file
    return f"{norm}:{rec.src_line}:{rec.name}"


def build_func_map(profiles: list[ProfileData]) -> dict[str, dict[str, ProfileRecord]]:
    lookup = {}
    for profile in profiles:
        lookup[profile.name] = {func_key(r): r for r in profile.records}
    return lookup


# ---------------------------------------------------------------------------
# Plot (with min/max whiskers)
# ---------------------------------------------------------------------------


def generate_plot(
    profile: ProfileData,
    plot_dir: Path,
    baseline_func_map: dict[str, ProfileRecord] | None = None,
) -> Path:
    top_n = profile.records[:TOP_N_PLOT]
    if not top_n:
        return plot_dir / f"{profile.name}.png"

    raw_times = [r.mean_ns for r in top_n]
    min_times_raw = [r.min_ns for r in top_n]
    max_times_raw = [r.max_ns for r in top_n]
    has_baseline = baseline_func_map is not None

    baseline_times_raw = []
    if has_baseline:
        for r in top_n:
            base_rec = baseline_func_map.get(func_key(r))
            baseline_times_raw.append(base_rec.mean_ns if base_rec else 0)

    all_times = raw_times + max_times_raw + (baseline_times_raw if has_baseline else [])
    unit_label, multiplier = best_unit_for_values_ns(all_times)
    mean_times = [t * multiplier for t in raw_times]
    min_times = [t * multiplier for t in min_times_raw]
    max_times = [t * multiplier for t in max_times_raw]
    baseline_times = (
        [t * multiplier for t in baseline_times_raw] if has_baseline else []
    )

    xerr_lo = [mean - mn for mean, mn in zip(mean_times, min_times, strict=False)]
    xerr_hi = [mx - mean for mean, mx in zip(mean_times, max_times, strict=False)]

    labels = truncate_labels([format_label(r) for r in top_n])
    fig, ax, y_pos = setup_plot(len(labels), has_baseline)

    err_kw = dict(
        xerr=[xerr_lo, xerr_hi],
        ecolor="#5BA3C7",
        capsize=2,
        error_kw={"linewidth": 0.8, "alpha": 0.7},
    )

    if has_baseline:
        bar_height = 0.35
        bars = ax.barh(
            y_pos - bar_height / 2,
            mean_times,
            height=bar_height,
            color=CLR_CURRENT,
            edgecolor="#5BA3C7",
            linewidth=0.5,
            label="Current",
            **err_kw,
        )
        draw_baseline_bars(ax, y_pos, baseline_times, bar_height)
    else:
        bar_height = 0.6
        bars = ax.barh(
            y_pos,
            mean_times,
            height=bar_height,
            color=CLR_CURRENT,
            edgecolor="#5BA3C7",
            linewidth=0.5,
            **err_kw,
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    max_val = (
        max(max_times + (baseline_times if has_baseline else [])) if max_times else 1
    )

    return finalize_plot(
        fig,
        ax,
        bars,
        max_val,
        f"Mean Time ({unit_label})  [whiskers: min/max]",
        plot_dir / f"{profile.name}.png",
    )


# ---------------------------------------------------------------------------
# Section builder
# ---------------------------------------------------------------------------


def build_section(
    profile: ProfileData,
    plot_path: Path,
    baseline_func_map: dict[str, ProfileRecord] | None = None,
) -> Section:
    has_baseline = baseline_func_map is not None
    section = Section(profile.name)
    section.add_text(f"Total Calls: {profile.total_calls:,}")
    section.add_figure(Figure(plot_path))

    columns = [
        Column("File", width="3cm", align="l"),
        Column("Function", width="3.5cm", align="l"),
        Column("Calls", align="r"),
        Column("Mean", align="r"),
        Column("Min", align="r"),
        Column("Max", align="r"),
        Column("Total\\%", align="r"),
    ]
    if has_baseline:
        columns.append(Column("Delta", align="r"))

    table = Table(columns, row_color_alt="rowalt")
    for rec in profile.records[:TOP_N_TABLE]:
        mean_val, mean_unit = format_time_ns(rec.mean_ns)
        min_val, min_unit = format_time_ns(rec.min_ns)
        max_val, max_unit = format_time_ns(rec.max_ns)
        src = (
            normalize_src_path(f"{rec.src_file}:{rec.src_line}")
            if rec.src_file
            else "built-in"
        )
        row = [
            escape(src),
            escape(rec.name),
            f"{rec.counts:,}",
            escape(f"{mean_val} {mean_unit}"),
            escape(f"{min_val} {min_unit}"),
            escape(f"{max_val} {max_unit}"),
            f"{rec.total_perc:.1f}\\%",
        ]
        if has_baseline:
            base_rec = baseline_func_map.get(func_key(rec))
            if base_rec:
                color = delta_color(rec.mean_ns, base_rec.mean_ns)
                delta_str = format_delta(rec.mean_ns, base_rec.mean_ns)
                row.append(f"\\textcolor{{{color}}}{{{delta_str}}}")
            else:
                row.append("\\textit{new}")
        table.add_row(row)

    section.add_table(table)
    return section


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_report(input_path: Path, output_path: Path, h5_path: Path | None):
    """Generate a performance report from Tracy CSV files."""
    await _generate_report(
        input_path,
        output_path,
        h5_path,
        extractor_cls=ProfileExtractor,
        storage_cls=ProfileStorage,
        generate_plot_fn=generate_plot,
        build_section_fn=build_section,
        build_func_map_fn=build_func_map,
        file_type_label="Tracy CSV",
    )
