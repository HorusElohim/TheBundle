import os
import re
import click
import pstats
import bundle 
import asyncio
import logging
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator
import latex

LOGGER = logging.getLogger(__name__)

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
    """
    Escapes special characters for LaTeX.
    """
    return re.sub(r"([_#%&${}])", r"\\\1", text)


def parse_function_name(function: str):
    # Use a regex to capture the file name and line number separately
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

        # Check if file_name is a placeholder like '~' for built-in functions
        if "~" in file_name:
            full_file_name = "built-in"
        else:
            full_file_name = f"{file_name}:{line_number}"

    return full_file_name, function_detail


def parse_function_name_plot(function: str):
    function_file, function_name = parse_function_name(function)
    return f"{function_file}  {function_name}"


@bundle.Data.dataclass
class ProfileFinder(bundle.Task):
    def exec(self, *args, **kwds):
        prof_files = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if file.endswith(".prof"):
                    prof_files.append(Path(root) / file)
        return prof_files


@bundle.Data.dataclass
class ProfileLoader(bundle.Task.Async):
    profile_data: list = bundle.Data.field(default_factory=list)
    total_calls: int = bundle.Data.field(default_factory=int)

    async def exec(self, *args, **kwds):
        self.stats = pstats.Stats(str(self.path))
        self.stats.strip_dirs().sort_stats("cumulative")
        for func, (cc, nc, tt, ct, callers) in self.stats.stats.items():
            self.profile_data.append(
                {"function": "{}:{}({})".format(*func), "total_calls": cc, "total_time": tt, "cumulative_time": ct}
            )
        self.profile_data = sorted(self.profile_data, key=lambda x: x["cumulative_time"], reverse=True)
        self.total_calls = sum(item["total_calls"] for item in self.profile_data)
        return self.profile_data


@bundle.Data.dataclass
class ProfilerPlot(bundle.Task.Async):
    plot_color_hex: str = "#D3D3D3"

    def setup_plot(self):
        fig, ax = plt.subplots()
        ax.set_facecolor("#2d2d2d")  # Dark gray background
        ax.grid(True, linestyle=":", color="#555555")  # Dotted grid lines
        return fig, ax

    def prepare_data_for_plot(self, profile_data):
        cumulative_times = [int(x["cumulative_time"] * 1e9) for x in profile_data[:10]]
        function_names = [parse_function_name_plot(x["function"]) for x in profile_data[:10]]
        return cumulative_times, function_names

    def create_barchart(self, ax, function_names, cumulative_times):
        return ax.barh(function_names, cumulative_times, color="skyblue")

    def configure_axes(self, ax, cumulative_times):
        ax.set_xlabel("Cumulative Time (ns)", color=self.plot_color_hex)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1e}"))
        x_tick_interval = max(cumulative_times) / 3
        ax.xaxis.set_major_locator(MultipleLocator(x_tick_interval))
        if cumulative_times:
            max_time = max(cumulative_times)
            ax.set_xlim(right=max_time * 1.1)
        ax.tick_params(axis="x", colors=self.plot_color_hex)
        ax.tick_params(axis="y", colors=self.plot_color_hex)

    def annotate_bars(self, ax, bars):
        for bar in bars:
            width = bar.get_width()
            label_x_pos, ha = self.determine_label_position(ax, width)
            ax.text(
                label_x_pos,
                bar.get_y() + bar.get_height() / 2,
                f"{width}",
                ha=ha,
                va="center",
                color="black",
                weight="bold",
            )

    def determine_label_position(self, ax, bar_width):
        if bar_width < ax.get_xlim()[1] * 0.01:
            ha = "left"
            label_x_pos = bar_width + ax.get_xlim()[1] * 0.005
        else:
            ha = "right"
            label_x_pos = bar_width
        return label_x_pos, ha

    async def exec(self, profile_data, *args, **kwds):
        fig, ax = self.setup_plot()
        cumulative_times, function_names = self.prepare_data_for_plot(profile_data)
        bars = self.create_barchart(ax, function_names, cumulative_times)
        self.configure_axes(ax, cumulative_times)
        self.annotate_bars(ax, bars)
        fig.savefig(self.path, transparent=True, bbox_inches="tight", pad_inches=0, dpi=300)
        plt.clf()

    def __del__(self):
        LOGGER.debug(f"cleaning plot: {self.path}")
        os.remove(self.path)
        return super().__del__()


@bundle.Data.dataclass
class ProfilerReportLatex(bundle.Task):
    main_folder: str = bundle.Data.field(default_factory=str)
    output_path: str = bundle.Data.field(default_factory=str)
    latex_content: str = bundle.Data.field(default_factory=str)

    def generate_table(self, profile_data):
        table_content = (
            "\\begin{longtable}{@{}p{0.15\\linewidth}p{0.35\\linewidth}lll@{}}\n"
            "\\toprule\n"
            "File & Function & Total Calls & Total Time (ns) & Cumulative Time (ns) \\\\\n"
            "\\midrule\n"
            "\\endfirsthead\n"
            "\\toprule\n"
            "File & Function & Total Calls & Total Time (ns) & Cumulative Time (ns) \\\\\n"
            "\\midrule\n"
            "\\endhead\n"
            "\\midrule\n"
            "\\multicolumn{5}{r}{{Continued on next page}} \\\\\n"
            "\\midrule\n"
            "\\endfoot\n"
            "\\bottomrule\n"
            "\\endlastfoot\n"
        )

        for item in profile_data:
            # Ensure that latex_escape is applied to each part of the text that needs it
            file_name, function_detail = parse_function_name(item["function"])
            file_name = latex_escape(file_name)
            function_detail = latex_escape(function_detail)
            total_time_ns = int(item["total_time"] * 1e9)
            cumulative_time_ns = int(item["cumulative_time"] * 1e9)
            # Apply latex_escape to each field that is inserted into the LaTeX code
            table_content += (
                f"{file_name} & {function_detail} & {item['total_calls']} & {total_time_ns} & {cumulative_time_ns} \\\\\n"
            )
        table_content += "\\end{longtable}\n"
        return table_content

    async def generate_plots(self):
        plot_tasks = [
            ProfilerPlot(
                profile_data=loader.profile_data,
                path=str((loader.path.parent / f"{loader.path.stem}_dark.png").absolute()),
            )
            for loader in self.profile_loaders
        ]
        return await asyncio.gather(*(plot_task() for plot_task in plot_tasks))

    def generate(self, prof_loaders: list[ProfileLoader], prof_plots: list[ProfilerPlot]):
        LOGGER.info(f"LateX generation ...")
        main_folder_name = latex_escape(self.main_folder)
        self.latex_content = (
            f"{LATEX_HEADER}"
            f"\\title{{\\color{{textcolor}}Profiler Report: {main_folder_name}}}"
            r"\author{TheBundle}"
            r"\maketitle"
            r"\tableofcontents "
            r"\newpage"
        )

        for loader, prof_plot in zip(prof_loaders, prof_plots):
            total_calls = loader.total_calls
            section_title = latex_escape(os.path.basename(loader.path))

            # Add the section title, image, and table content on the same page
            self.latex_content += (
                f"\\section{{{section_title}}}\n"
                f"Total Calls: {total_calls}\n\n"
                f"\\begin{{figure}}[htbp]\n\\centering\n"
                f"\\includegraphics[width=1\\linewidth]{{{prof_plot.path}}}\n"
                "\\end{figure}\n"
                f"{self.generate_table(loader.profile_data)}"
                "\\clearpage\n"  # Ensures that tables do not exceed one page
            )

        self.latex_content += r"\end{document}"
        LOGGER.info(f"LateX generation {bundle.core.logger.Emoji.success}")

    def build(self):
        # Generate PDF from LaTeX content
        LOGGER.info(f"LateX building ...")
        pdf = latex.build_pdf(self.latex_content)
        LOGGER.info(f"LateX build {bundle.core.logger.Emoji.success}")
        pdf.save_to(self.output_path)
        LOGGER.info(f"LateX saved to {self.output_path}")

    def exec(self, prof_loaders: list[ProfileLoader], prof_plots: list[ProfilerPlot], *args, **kwds):
        self.generate(prof_loaders, prof_plots)
        self.build()


@bundle.Data.dataclass
class MainProfilerReport(bundle.Task):
    input_path: str = bundle.Data.field(default_factory=str)
    output_path: str = bundle.Data.field(default_factory=str)

    async def run_loader_and_plot_generator(self, loader, plot_generator):
        await loader()
        await plot_generator(loader.profile_data)
        return loader, plot_generator

    async def run_all(self, prof_files):
        tasks = []
        for prof_file in prof_files:
            loader = ProfileLoader(path=prof_file)
            plot_file = str((prof_file.parent / f"{prof_file.stem}_dark.png").absolute())
            plot_generator = ProfilerPlot(path=plot_file)
            task = self.run_loader_and_plot_generator(loader, plot_generator)
            tasks.append(task)
        return await asyncio.gather(*tasks)

    def exec(self, *args, **kwds):
        # Find .prof files
        prof_files = ProfileFinder(path=self.input_path)()

        # Run loaders and plot generators concurrently
        results = asyncio.run(self.run_all(prof_files))

        # Unpack results into loaders and plot_generators
        loaders, plot_generators = zip(*results)

        # Generate report
        ProfilerReportLatex(output_path=self.output_path, main_folder=self.input_path)(loaders, plot_generators)


@click.command()
@click.option("--input_path", help="Path to search for .prof files", required=True)
@click.option("--output_path", help="Path to save the LaTeX report", required=True)
def main(input_path, output_path):
    LOGGER.info("Program start")
    task = MainProfilerReport(input_path=input_path, output_path=output_path)
    task()
    LOGGER.info(f"Run {bundle.core.logger.Emoji.success} in {task.duration * 1e-9:.2f} seconds")


if __name__ == "__main__":
    main()
