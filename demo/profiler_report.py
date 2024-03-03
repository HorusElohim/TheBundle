import os
import re
import click
import pstats
import asyncio
from pathlib import Path
import matplotlib
import shutil

matplotlib.use("Agg")  # Use the Agg backend to prevent Tkinter issues
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
import latex
from bundle.core.data import Data, Field
from bundle.core import logger
from enum import Enum

LOGGER = logger.setup_root_logger(name=__name__)

MAX_PARALLEL_ASYNC = 20

LATEX_HEADER = r"""
    \documentclass{article}
    \usepackage{graphicx}
    \usepackage[table]{xcolor}
    \usepackage{geometry}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{hyperref}
    \usepackage[utf8]{inputenc}
    \geometry{margin=1in}
    \definecolor{backgroundcolor}{HTML}{121212}
    \definecolor{textcolor}{HTML}{E0E0E0}
    \definecolor{plotcolor}{HTML}{D3D3D3}
    \pagecolor{backgroundcolor}
    \color{textcolor}
    \begin{document}
"""


def latex_escape(text: str):
    return re.sub(r"([_#%&${}])", r"\\\1", text)


def parse_function_name(function: str):
    match = re.match(r"^(.*):(\d+)(\(.*\))$", function)
    full_file_name = "N/A"
    function_detail = "N/A"
    if match:
        file_name = match.group(1)
        line_number = match.group(2)
        function_detail = match.group(3)
        function_detail = (
            function_detail.replace("<", "")
            .replace(">", "")
            .replace("method", "")
            .replace("built-in", "")
            .replace("(", "")
            .replace(")", "")
        )

        if "~" in file_name:
            full_file_name = "built-in"
        else:
            full_file_name = f"{file_name}:{line_number}"

    return full_file_name, function_detail


def parse_function_name_plot(function: str):
    function_file, function_name = parse_function_name(function)
    return f"{function_file}  {function_name}"


class TimeScale(Enum):
    SECOND = "second"
    MILLISECOND = "millisecond"
    MICROSECOND = "microsecond"
    NANOSECOND = "nanosecond"


class ProfileFunction(Data):
    function: str
    total_calls: int
    total_time: float
    cumulative_time: float


class ProfileData(Data):
    prof_path: Path
    data: list[ProfileFunction] = Field(default_factory=list)
    total_calls: int = 0
    plot_path: Path = Field(default_factory=Path)

    def add(self, x: ProfileFunction):
        self.data.append(x)

    def sort(self):
        self.data = sorted(self.data, key=lambda x: x.cumulative_time, reverse=True)

    def compute_total_calls(self):
        self.total_calls = sum(x.total_calls for x in self.data)


class ProfilerReportGenerator:
    def __init__(self, input_path: Path, output_path: Path, time_scale: TimeScale):
        self.input_path = input_path
        self.output_path = output_path
        self.time_scale = time_scale
        self.profile_data_list: list[ProfileData] = []

    def get_time_multiplier(self):
        if self.time_scale == TimeScale.SECOND:
            return 1
        elif self.time_scale == TimeScale.MILLISECOND:
            return 1e3
        elif self.time_scale == TimeScale.MICROSECOND:
            return 1e6
        elif self.time_scale == TimeScale.NANOSECOND:
            return 1e9

    def get_time_unit(self):
        if self.time_scale == TimeScale.SECOND:
            return "s"
        elif self.time_scale == TimeScale.MILLISECOND:
            return "ms"
        elif self.time_scale == TimeScale.MICROSECOND:
            return "μs"
        elif self.time_scale == TimeScale.NANOSECOND:
            return "ns"

    async def run(self):
        await self.find_all_profiler_paths()
        if not self.prof_paths:
            LOGGER.warning("No .prof files found in the specified input path.")
            return
        await self.process_profiles()
        await self.generate_latex_report()

    async def find_all_profiler_paths(self):
        def _find_paths():
            prof_paths = []
            for root, _, files in os.walk(self.input_path):
                for file in files:
                    if file.endswith(".prof"):
                        prof_paths.append(Path(root) / file)
            return prof_paths

        self.prof_paths = await asyncio.to_thread(_find_paths)

    async def process_profiles(self):
        semaphore = asyncio.Semaphore(MAX_PARALLEL_ASYNC)

        async def sem_process_profile(prof_path):
            async with semaphore:
                return await self.process_profile(prof_path)

        tasks = [sem_process_profile(prof_path) for prof_path in self.prof_paths]
        self.profile_data_list = await asyncio.gather(*tasks)

    async def process_profile(self, prof_path: Path) -> ProfileData:
        profile_data = await self.load_profile_data(prof_path)
        await self.generate_profiler_plot(profile_data)
        return profile_data

    async def load_profile_data(self, prof_path: Path) -> ProfileData:
        def _load_data():
            profile_data = ProfileData(prof_path=prof_path)
            stats = pstats.Stats(str(prof_path))
            stats.strip_dirs().sort_stats("cumulative")
            for func, (cc, nc, tt, ct, callers) in stats.stats.items():
                function_str = "{}:{}({})".format(*func)
                profile_data.add(
                    ProfileFunction(
                        function=function_str,
                        total_calls=cc,
                        total_time=tt,
                        cumulative_time=ct,
                    )
                )
            profile_data.sort()
            profile_data.compute_total_calls()
            LOGGER.info(f"Parsed {prof_path.as_posix()}")
            return profile_data

        return await asyncio.to_thread(_load_data)

    async def generate_profiler_plot(self, profile_data: ProfileData):
        def _generate_plot():
            fig, ax = plt.subplots()
            ax.set_facecolor("#2d2d2d")  # Dark gray background
            ax.grid(True, linestyle=":", color="#555555")  # Dotted grid lines

            multiplier = self.get_time_multiplier()
            cumulative_times = [x.cumulative_time * multiplier for x in profile_data.data[:10]]
            function_names = [parse_function_name_plot(x.function) for x in profile_data.data[:10]]

            # Create the bar chart
            bars = self.create_barchart(ax, function_names, cumulative_times)
            self.configure_axes(ax, cumulative_times)
            self.annotate_bars(ax, bars)

            plot_path = profile_data.prof_path.with_suffix(".png")
            fig.savefig(
                plot_path,
                transparent=True,
                bbox_inches="tight",
                pad_inches=0,
                dpi=300,
            )
            LOGGER.info("Plot saved: %s", plot_path)
            profile_data.plot_path = plot_path
            plt.close(fig)  # Close the figure to free up memory

        await asyncio.to_thread(_generate_plot)

    def create_barchart(self, ax, function_names, cumulative_times):
        """
        Create a horizontal bar chart.
        """
        return ax.barh(function_names, cumulative_times, color="skyblue")

    def configure_axes(self, ax, cumulative_times):
        """
        Configure the axes, labels, and ticks.
        """
        unit_label = self.get_time_unit()
        ax.set_xlabel(f"Cumulative Time ({unit_label})", color="#D3D3D3")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.3f}"))
        x_tick_interval = max(cumulative_times) / 3 if cumulative_times else 1
        ax.xaxis.set_major_locator(MultipleLocator(x_tick_interval))
        if cumulative_times:
            max_time = max(cumulative_times)
            ax.set_xlim(right=max_time * 1.1)
        ax.tick_params(axis="x", colors="#D3D3D3")
        ax.tick_params(axis="y", colors="#D3D3D3")

    def annotate_bars(self, ax, bars):
        """
        Annotate bars with their width values.
        """
        for bar in bars:
            width = bar.get_width()
            label_x_pos, ha = self.determine_label_position(ax, width)
            ax.text(
                label_x_pos,
                bar.get_y() + bar.get_height() / 2,
                f"{width:.3f}",
                ha=ha,
                va="center",
                color="black",
                weight="bold",
            )

    def determine_label_position(self, ax, bar_width):
        """
        Determine the label position and alignment based on bar width.
        """
        if bar_width < ax.get_xlim()[1] * 0.01:
            ha = "left"
            label_x_pos = bar_width + ax.get_xlim()[1] * 0.005
        else:
            ha = "right"
            label_x_pos = bar_width
        return label_x_pos, ha

    async def generate_latex_report(self):
        LOGGER.info("LaTeX building ...")
        target_folder = latex_escape(str(self.input_path.as_posix()))
        latex_content = [
            f"{LATEX_HEADER}",
            f"\\title{{\\color{{textcolor}}Profiler Report: {target_folder}}}",
            r"\author{TheBundle}",
            r"\maketitle",
            r"\tableofcontents ",
            r"\newpage",
        ]

        async def generate_section(profile_data):
            prof_path = latex_escape(str(profile_data.prof_path.name))
            plot_path = latex_escape(str(profile_data.plot_path.as_posix()))
            table_content = self.generate_table(profile_data)
            section_content = (
                f"\\section{{ {{ {prof_path} }}}}\n"
                f"Total Calls: {profile_data.total_calls}\n\n"
                "\\begin{figure}[htbp]\\centering\n"
                f"\\includegraphics[width=1\\linewidth] {{{{ {plot_path} }}}}\n"
                "\\end{figure}\n"
                f"{table_content}"
                "\\clearpage\n"
            )
            return section_content

        # Generate sections concurrently
        LOGGER.info("LaTeX constructing content ...")
        tasks = [generate_section(pd) for pd in self.profile_data_list]
        sections = await asyncio.gather(*tasks)
        latex_content.extend(sections)
        latex_content.append(r"\end{document}")
        latex_content_str = "".join(latex_content)

        # Build PDF
        pdf = await asyncio.to_thread(latex.build_pdf, latex_content_str)
        LOGGER.info("LaTeX build success")

        # Save PDF
        await asyncio.to_thread(pdf.save_to, self.output_path)
        LOGGER.info(f"LaTeX saved to {self.output_path}")

        LOGGER.info("LaTeX cleaning resources...")
        # Clean up resources concurrently
        cleanup_tasks = [asyncio.to_thread(os.remove, profile_data.plot_path) for profile_data in self.profile_data_list]
        await asyncio.gather(*cleanup_tasks)

    def generate_table(self, profile_data: ProfileData):
        unit_label = self.get_time_unit()
        table_lines = [
            "\\begin{longtable}{@{}p{0.15\\linewidth}p{0.35\\linewidth}lll@{}}\n",
            "\\toprule\n",
            f"File & Function & Total Calls & Total Time ({unit_label}) & Cumulative Time ({unit_label}) \\\\\n",
            "\\midrule\n",
            "\\endfirsthead\n",
            "\\toprule\n",
            f"File & Function & Total Calls & Total Time ({unit_label}) & Cumulative Time ({unit_label}) \\\\\n",
            "\\midrule\n",
            "\\endhead\n",
            "\\midrule\n",
            "\\multicolumn{5}{r}{{Continued on next page}} \\\\\n",
            "\\midrule\n",
            "\\endfoot\n",
            "\\bottomrule\n",
            "\\endlastfoot\n",
        ]

        multiplier = self.get_time_multiplier()
        for prof_func in profile_data.data:
            file_name, function_detail = parse_function_name(prof_func.function)
            file_name = latex_escape(file_name)
            function_detail = latex_escape(function_detail)
            total_time_scaled = prof_func.total_time * multiplier
            cumulative_time_scaled = prof_func.cumulative_time * multiplier
            table_lines.append(
                f"{file_name} & {function_detail} & {prof_func.total_calls} & {total_time_scaled:.3f} & {cumulative_time_scaled:.3f} \\\\\n"
            )
        table_lines.append("\\end{longtable}\n")
        return "".join(table_lines)


@click.command()
@click.option("--input_path", "-i", help="Path to search for .prof files", required=True)
@click.option("--output_path", "-o", help="Path to save the LaTeX report", required=True)
@click.option(
    "--time-scale",
    "-t",
    type=click.Choice([e.value for e in TimeScale], case_sensitive=False),
    default="nanosecond",
    help="Time scale for output times",
)
def main(input_path, output_path, time_scale):
    time_scale_enum = TimeScale(time_scale.lower())
    profiler = ProfilerReportGenerator(Path(input_path), Path(output_path), time_scale_enum)
    asyncio.run(profiler.run())


if __name__ == "__main__":
    main()
