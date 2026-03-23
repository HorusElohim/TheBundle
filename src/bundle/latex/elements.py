# Copyright 2026 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import re
from pathlib import Path


def escape(text: str) -> str:
    """Escape special LaTeX characters in a string."""
    text = text.replace("\\", "/")
    # Escape special chars first, then substitute unicode symbols
    # (μ → $\mu$ must come after $ escaping to avoid double-escape)
    text = re.sub(r"([_#%&${}])", r"\\\1", text)
    text = text.replace("\u03bc", "$\\mu$")
    return text


class Column:
    """Defines a table column with alignment and width."""

    def __init__(self, header: str, width: str | None = None, align: str = "l"):
        self.header = header
        self.width = width
        self.align = align

    def spec(self) -> str:
        if self.width:
            return f">{{{self._align_cmd()}}}p{{{self.width}}}"
        return self.align

    def _align_cmd(self) -> str:
        mapping = {"l": "\\RaggedRight", "r": "\\RaggedLeft", "c": "\\Centering"}
        return mapping.get(self.align, "\\RaggedRight")


class Table:
    """Build a LaTeX longtable from column definitions and row data."""

    def __init__(self, columns: list[Column], row_color_alt: str | None = None):
        self.columns = columns
        self.row_color_alt = row_color_alt
        self._rows: list[list[str]] = []

    def add_row(self, values: list[str]):
        self._rows.append(values)

    def render(self) -> str:
        col_specs = " ".join(c.spec() for c in self.columns)
        lines = ["{\\small\n"]
        if self.row_color_alt:
            lines.append(
                f"\\rowcolors{{2}}{{{self.row_color_alt}}}{{backgroundcolor}}\n"
            )
        lines.append(f"\\begin{{longtable}}{{@{{}}{col_specs}@{{}}}}\n")
        # Header
        header_line = self._render_header()
        lines.extend(
            [
                "\\toprule\n",
                "\\rowcolor{backgroundcolor}\n",
                header_line,
                "\\midrule\n",
                "\\endfirsthead\n",
                "\\toprule\n",
                "\\rowcolor{backgroundcolor}\n",
                header_line,
                "\\midrule\n",
                "\\endhead\n",
                "\\midrule\n",
                f"\\multicolumn{{{len(self.columns)}}}{{r}}{{\\textit{{Continued on next page}}}} \\\\\n",
                "\\endfoot\n",
                "\\bottomrule\n",
                "\\endlastfoot\n",
            ]
        )
        for row in self._rows:
            lines.append(" & ".join(row) + " \\\\\n")
        lines.append("\\end{longtable}\n}\n")
        return "".join(lines)

    def _render_header(self) -> str:
        headers = [f"\\textbf{{{c.header}}}" for c in self.columns]
        return " & ".join(headers) + " \\\\\n"


class Figure:
    """Render a LaTeX figure with includegraphics."""

    def __init__(
        self,
        image_path: Path | str,
        width: str = "0.85\\linewidth",
        caption: str | None = None,
    ):
        self.image_path = escape(str(image_path).replace("\\", "/"))
        self.width = width
        self.caption = caption

    def render(self) -> str:
        lines = [
            "\\begin{figure}[htbp]\\centering\n",
            f"\\includegraphics[width={self.width}]{{{{{self.image_path}}}}}\n",
        ]
        if self.caption:
            lines.append(f"\\caption{{{escape(self.caption)}}}\n")
        lines.append("\\end{figure}\n")
        return "".join(lines)


class Section:
    """Render a LaTeX section with optional content blocks."""

    def __init__(self, title: str, level: int = 1):
        self.title = title
        self.level = level
        self._blocks: list[str] = []

    def add_text(self, text: str):
        self._blocks.append(text + "\n\n")

    def add_figure(self, figure: Figure):
        self._blocks.append(figure.render())

    def add_table(self, table: Table):
        self._blocks.append(table.render())

    def add_raw(self, latex_str: str):
        self._blocks.append(latex_str)

    def render(self) -> str:
        cmd = {1: "section", 2: "subsection", 3: "subsubsection"}.get(
            self.level, "section"
        )
        lines = [f"\\{cmd}{{ {escape(self.title)} }}\n"]
        lines.extend(self._blocks)
        lines.append("\\clearpage\n")
        return "".join(lines)
