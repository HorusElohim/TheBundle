import asyncio
import os
import tempfile
from pathlib import Path

import click
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
from bundle.perf_report import ProfileExtractor, ProfileStorage
from bundle.perf_report.extractor import ProfileData, ProfileRecord

LOGGER = logger.setup_root_logger(name=__name__)

MAX_PARALLEL_ASYNC = 20

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


def format_time_auto(seconds: float) -> tuple[str, str]:
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


def format_delta(current: float, baseline: float) -> str:
    if baseline == 0:
        return "--"
    pct = ((current - baseline) / baseline) * 100
    if abs(pct) < 0.5:
        return "~0\\%"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.0f}\\%"


def delta_color(current: float, baseline: float) -> str:
    if baseline == 0:
        return "textcolor"
    pct = ((current - baseline) / baseline) * 100
    if pct < -2:
        return "green"
    elif pct > 2:
        return "red"
    return "textcolor"


def best_unit_for_values(times_seconds: list[float]) -> tuple[str, float]:
    if not times_seconds:
        return "ns", 1e9
    max_val = max(abs(t) for t in times_seconds if t != 0) if any(t != 0 for t in times_seconds) else 0
    for threshold, unit, multiplier in TIME_THRESHOLDS:
        if max_val >= threshold:
            return unit, multiplier
    return "ns", 1e9


def shorten_path(file_path: str, max_parts: int = 2) -> str:
    file_path = file_path.replace("\\", "/")
    if file_path in ("N/A", "built-in", "~"):
        return file_path
    parts = file_path.split("/")
    if len(parts) <= max_parts:
        return file_path
    return "/".join(parts[-max_parts:])


def format_label(record: ProfileRecord) -> str:
    if "~" in record.file or record.file == "":
        return f"built-in  {record.function}"
    short = shorten_path(f"{record.file}:{record.line_number}")
    return f"{short}  {record.function}"


def _func_key(rec: ProfileRecord) -> str:
    return f"{rec.file}:{rec.line_number}:{rec.function}"


def _build_func_map(profiles: list[ProfileData]) -> dict[str, dict[str, ProfileRecord]]:
    """Build profile_name -> {func_key -> ProfileRecord} lookup."""
    lookup = {}
    for profile in profiles:
        lookup[profile.name] = {_func_key(r): r for r in profile.records}
    return lookup


def _get_platform_id() -> str:
    return f"{platform_info.system}-{platform_info.arch}-{platform_info.python_implementation}{platform_info.python_version}"


def _get_platform_meta() -> dict:
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


# ---------------------------------------------------------------------------
# Plot generation
# ---------------------------------------------------------------------------


def generate_plot(
    profile: ProfileData,
    plot_dir: Path,
    baseline_func_map: dict[str, ProfileRecord] | None = None,
) -> Path:
    top_n = profile.records[:10]
    if not top_n:
        return plot_dir / f"{profile.name}.png"

    raw_times = [r.cumulative_time for r in top_n]
    has_baseline = baseline_func_map is not None

    baseline_times_raw = []
    if has_baseline:
        for r in top_n:
            base_rec = baseline_func_map.get(_func_key(r))
            baseline_times_raw.append(base_rec.cumulative_time if base_rec else 0.0)

    all_times = raw_times + (baseline_times_raw if has_baseline else [])
    unit_label, multiplier = best_unit_for_values(all_times)
    cumulative_times = [t * multiplier for t in raw_times]
    baseline_times = [t * multiplier for t in baseline_times_raw] if has_baseline else []

    labels = [format_label(r) for r in top_n]
    max_label_len = 50
    labels = [la if len(la) <= max_label_len else "..." + la[-(max_label_len - 3) :] for la in labels]

    fig_height = max(3, len(top_n) * (0.7 if has_baseline else 0.5) + 1)
    fig, ax = plt.subplots(figsize=(10, fig_height))
    fig.patch.set_facecolor("#121212")
    ax.set_facecolor("#1E1E1E")
    ax.grid(True, linestyle=":", color="#333333", alpha=0.5, axis="x")

    y_pos = np.arange(len(labels))

    if has_baseline:
        bar_height = 0.35
        bars_current = ax.barh(
            y_pos - bar_height / 2,
            cumulative_times,
            height=bar_height,
            color=CLR_CURRENT,
            edgecolor="#5BA3C7",
            linewidth=0.5,
            label="Current",
        )
        ax.barh(
            y_pos + bar_height / 2,
            baseline_times,
            height=bar_height,
            color=CLR_BASELINE,
            edgecolor="#CC7055",
            linewidth=0.5,
            label="Baseline",
        )
        ax.legend(loc="lower right", fontsize=7, facecolor="#2d2d2d", edgecolor="#555555", labelcolor="#D3D3D3")
    else:
        bar_height = 0.6
        bars_current = ax.barh(
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
    ax.set_xlabel(f"Cumulative Time ({unit_label})", color="#D3D3D3", fontsize=9)

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
    ax.tick_params(axis="x", colors="#D3D3D3", labelsize=8)
    ax.tick_params(axis="y", colors="#D3D3D3", labelsize=7)

    xlim_max = ax.get_xlim()[1]
    for bar in bars_current:
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
        ax.text(lx, bar.get_y() + bar.get_height() / 2, label, ha=ha, va="center", color=color, weight="bold", fontsize=7)

    ax.invert_yaxis()
    for spine in ax.spines.values():
        spine.set_color("#333333")

    plot_path = plot_dir / f"{profile.name}.png"
    fig.savefig(plot_path, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.2, dpi=200)
    plt.close(fig)
    LOGGER.info("Plot saved: %s", plot_path)
    return plot_path


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _short_file(rec: ProfileRecord) -> str:
    if "~" in rec.file or rec.file == "":
        return "built-in"
    return shorten_path(f"{rec.file}:{rec.line_number}")


def build_platform_section(meta: dict) -> Section:
    """Build a platform info summary table from HDF5 metadata."""
    section = Section("Platform Info", level=1)

    columns = [
        Column("Property", width="4cm", align="l"),
        Column("Value", width="10cm", align="l"),
    ]
    table = Table(columns, row_color_alt="rowalt")

    display_keys = [
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
    ]

    for key, label in display_keys:
        val = meta.get(key, "")
        if val:
            table.add_row([escape(label), escape(str(val))])

    section.add_table(table)
    return section


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
        Column("Function", width="4.5cm", align="l"),
        Column("Calls", align="r"),
        Column("Total Time", align="r"),
        Column("Cumul. Time", align="r"),
    ]
    if has_baseline:
        columns.append(Column("Delta", align="r"))

    table = Table(columns, row_color_alt="rowalt")

    for rec in profile.records:
        total_val, total_unit = format_time_auto(rec.total_time)
        cumul_val, cumul_unit = format_time_auto(rec.cumulative_time)

        row = [
            escape(_short_file(rec)),
            escape(rec.function),
            f"{rec.call_count:,}",
            escape(f"{total_val} {total_unit}"),
            escape(f"{cumul_val} {cumul_unit}"),
        ]

        if has_baseline:
            base_rec = baseline_func_map.get(_func_key(rec))
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
# Report generation
# ---------------------------------------------------------------------------


async def _generate_plots(profiles, plot_dir, baseline_lookup=None):
    """Generate plots for all profiles, with optional baseline comparison."""
    semaphore = asyncio.Semaphore(MAX_PARALLEL_ASYNC)

    async def gen(profile):
        async with semaphore:
            func_map = baseline_lookup.get(profile.name) if baseline_lookup else None
            return profile, await asyncio.to_thread(generate_plot, profile, plot_dir, func_map)

    return await asyncio.gather(*[gen(p) for p in profiles])


def _cleanup_plots(results):
    for _, plot_path in results:
        try:
            os.remove(plot_path)
        except OSError:
            pass


def _find_baseline_version(storage: ProfileStorage, current_version: str, platform_id: str) -> str | None:
    """Find the most recent version in HDF5 that isn't the current one and has this platform."""
    versions = storage.list_versions()
    for version in reversed(versions):
        if version == current_version:
            continue
        platforms = storage.list_platforms(version)
        if platform_id in platforms:
            return version
    return None


async def generate_report(input_path: Path, output_path: Path, h5_path: Path | None):
    """Generate a performance report, auto-including comparison if a baseline exists in HDF5."""
    pid = _get_platform_id()
    pmeta = _get_platform_meta()

    LOGGER.info("Extracting profiles from %s", input_path)
    profiles = await asyncio.to_thread(ProfileExtractor.extract_all, input_path)
    if not profiles:
        LOGGER.warning("No .prof files found in %s", input_path)
        return

    LOGGER.info("Found %d profiles", len(profiles))

    current_version_key = _safe_key(bundle_version)

    # Save to HDF5
    if h5_path:
        machine_id = platform_info.node
        LOGGER.info("Saving HDF5 to %s (version=%s, platform=%s)", h5_path, bundle_version, pid)
        await asyncio.to_thread(
            ProfileStorage.from_directory,
            input_path,
            h5_path,
            machine_id,
            bundle_version,
            pid,
            pmeta,
        )

    # Try to find a baseline for comparison
    baseline_lookup = None
    baseline_version = None
    baseline_meta = None
    if h5_path and h5_path.exists():
        storage = ProfileStorage(h5_path)
        # list_versions / list_platforms return raw HDF5 keys (already safe-keyed)
        # load_profiles / load_meta apply _safe_key internally, but it's idempotent
        baseline_version = _find_baseline_version(storage, current_version_key, _safe_key(pid))
        if baseline_version:
            LOGGER.info("Found baseline version: %s", baseline_version)
            baseline_profiles = await asyncio.to_thread(storage.load_profiles, baseline_version, pid)
            baseline_meta = await asyncio.to_thread(storage.load_meta, baseline_version, pid)
            if baseline_profiles:
                baseline_lookup = _build_func_map(baseline_profiles)

    has_comparison = baseline_lookup is not None
    plot_dir = Path(tempfile.mkdtemp(prefix="profiler_plots_"))
    results = await _generate_plots(profiles, plot_dir, baseline_lookup)

    # Build document
    LOGGER.info("Building LaTeX document ...")
    title = f"Performance Report: {escape(bundle_version)}"
    if has_comparison:
        base_ver = baseline_meta.get("bundle_version", baseline_version) if baseline_meta else baseline_version
        title = f"Performance Report: {escape(bundle_version)} vs {escape(str(base_ver))}"

    doc = Document(title=title)
    if has_comparison:
        doc.add_preamble("\\definecolor{green}{HTML}{66BB6A}\n")
        doc.add_preamble("\\definecolor{red}{HTML}{EF5350}\n")

    # Platform info section
    meta_for_table = {**pmeta, "bundle_version": bundle_version}
    doc.add_section(build_platform_section(meta_for_table))

    # Profile sections
    for profile, plot_path in results:
        func_map = baseline_lookup.get(profile.name) if baseline_lookup else None
        doc.add_section(build_section(profile, plot_path, func_map))

    LOGGER.info("Compiling PDF ...")
    await asyncio.to_thread(doc.save_pdf, output_path)
    LOGGER.info("PDF saved to %s", output_path)
    _cleanup_plots(results)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _safe_key(v: str) -> str:
    return v.replace("+", "_").replace("/", "_").replace("\\", "_")


@click.command()
@click.option("--input-path", "-i", required=True, help="Directory with .prof files")
@click.option("--output-dir", "-o", required=True, help="Output directory")
@click.option("--h5/--no-h5", default=True, help="Save HDF5 data alongside PDF")
@click.option("--pdf-name", default=None, help="PDF filename (default: perf_report_<version>_<platform>.pdf)")
def report(input_path, output_dir, h5, pdf_name):
    """Generate a performance report from .prof files, with auto-comparison."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    pid = _get_platform_id()

    if pdf_name is None:
        pdf_name = f"perf_report_{_safe_key(bundle_version)}_{_safe_key(pid)}.pdf"

    pdf_path = out / pdf_name
    h5_path = out / "profiles.h5" if h5 else None
    asyncio.run(generate_report(Path(input_path), pdf_path, h5_path))


if __name__ == "__main__":
    report()
