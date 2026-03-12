"""cProfile-based performance report: per-test .prof files with call trees."""

from pathlib import Path

from bundle.latex import Figure, Section, Table, escape
from bundle.latex.elements import Column
from bundle.perf_report.extractor import CProfileData, CProfileExtractor, CProfileRecord
from bundle.perf_report.storage import CProfileStorage

from .base import (
    CLR_CURRENT,
    TOP_N_PLOT,
    TOP_N_TABLE,
    best_unit_for_values_seconds,
    delta_color,
    draw_baseline_bars,
    finalize_plot,
    format_delta,
    format_time_seconds,
    setup_plot,
    shorten_path,
    truncate_labels,
)
from .base import (
    generate_report as _generate_report,
)

# ---------------------------------------------------------------------------
# cProfile-specific helpers
# ---------------------------------------------------------------------------


def format_label(rec: CProfileRecord) -> str:
    if "~" in rec.file or rec.file == "":
        return f"built-in  {rec.function}"
    return f"{shorten_path(f'{rec.file}:{rec.line_number}')}  {rec.function}"


def func_key(rec: CProfileRecord) -> str:
    return f"{rec.file}:{rec.line_number}:{rec.function}"


def build_func_map(profiles: list[CProfileData]) -> dict[str, dict[str, CProfileRecord]]:
    lookup = {}
    for profile in profiles:
        lookup[profile.name] = {func_key(r): r for r in profile.records}
    return lookup


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------


def generate_plot(
    profile: CProfileData,
    plot_dir: Path,
    baseline_func_map: dict[str, CProfileRecord] | None = None,
) -> Path:
    top_n = profile.records[:TOP_N_PLOT]
    if not top_n:
        return plot_dir / f"{profile.name}.png"

    raw_times = [r.cumulative_time for r in top_n]
    has_baseline = baseline_func_map is not None

    baseline_times_raw = []
    if has_baseline:
        for r in top_n:
            base_rec = baseline_func_map.get(func_key(r))
            baseline_times_raw.append(base_rec.cumulative_time if base_rec else 0.0)

    all_times = raw_times + (baseline_times_raw if has_baseline else [])
    unit_label, multiplier = best_unit_for_values_seconds(all_times)
    cumulative_times = [t * multiplier for t in raw_times]
    baseline_times = [t * multiplier for t in baseline_times_raw] if has_baseline else []

    labels = truncate_labels([format_label(r) for r in top_n])
    fig, ax, y_pos = setup_plot(len(labels), has_baseline)

    if has_baseline:
        bar_height = 0.35
        bars = ax.barh(
            y_pos - bar_height / 2,
            cumulative_times,
            height=bar_height,
            color=CLR_CURRENT,
            edgecolor="#5BA3C7",
            linewidth=0.5,
            label="Current",
        )
        draw_baseline_bars(ax, y_pos, baseline_times, bar_height)
    else:
        bar_height = 0.6
        bars = ax.barh(
            y_pos,
            cumulative_times,
            height=bar_height,
            color=CLR_CURRENT,
            edgecolor="#5BA3C7",
            linewidth=0.5,
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    max_val = max(cumulative_times + (baseline_times if has_baseline else [])) if cumulative_times else 1

    return finalize_plot(fig, ax, bars, max_val, f"Cumulative Time ({unit_label})", plot_dir / f"{profile.name}.png")


# ---------------------------------------------------------------------------
# Section builder
# ---------------------------------------------------------------------------


def _short_file(rec: CProfileRecord) -> str:
    if "~" in rec.file or rec.file == "":
        return "built-in"
    return shorten_path(f"{rec.file}:{rec.line_number}")


def build_section(
    profile: CProfileData,
    plot_path: Path,
    baseline_func_map: dict[str, CProfileRecord] | None = None,
) -> Section:
    has_baseline = baseline_func_map is not None
    section = Section(profile.name)
    section.add_text(f"Total Calls: {profile.total_calls:,}")
    section.add_figure(Figure(plot_path))

    columns = [
        Column("File", width="3cm", align="l"),
        Column("Function", width="4.5cm", align="l"),
        Column("Calls", align="r"),
        Column("Total Time", align="r"),
        Column("Cumul. Time", align="r"),
    ]
    if has_baseline:
        columns.append(Column("Delta", align="r"))

    table = Table(columns, row_color_alt="rowalt")
    for rec in profile.records[:TOP_N_TABLE]:
        total_val, total_unit = format_time_seconds(rec.total_time)
        cumul_val, cumul_unit = format_time_seconds(rec.cumulative_time)
        row = [
            escape(_short_file(rec)),
            escape(rec.function),
            f"{rec.call_count:,}",
            escape(f"{total_val} {total_unit}"),
            escape(f"{cumul_val} {cumul_unit}"),
        ]
        if has_baseline:
            base_rec = baseline_func_map.get(func_key(rec))
            if base_rec:
                color = delta_color(rec.cumulative_time, base_rec.cumulative_time)
                delta_str = format_delta(rec.cumulative_time, base_rec.cumulative_time)
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
    """Generate a performance report from .prof files."""
    await _generate_report(
        input_path,
        output_path,
        h5_path,
        extractor_cls=CProfileExtractor,
        storage_cls=CProfileStorage,
        generate_plot_fn=generate_plot,
        build_section_fn=build_section,
        build_func_map_fn=build_func_map,
        file_type_label=".prof",
    )
