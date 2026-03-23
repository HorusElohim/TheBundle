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

from pathlib import Path

import latex as latex_lib

from .elements import Section


class Theme:
    """Color theme for a LaTeX document."""

    def __init__(
        self,
        background: str = "121212",
        text: str = "E0E0E0",
        accent: str = "87CEEB",
        row_alt: str = "1E1E1E",
    ):
        self.background = background
        self.text = text
        self.accent = accent
        self.row_alt = row_alt

    def preamble(self) -> str:
        return (
            f"\\definecolor{{backgroundcolor}}{{HTML}}{{{self.background}}}\n"
            f"\\definecolor{{textcolor}}{{HTML}}{{{self.text}}}\n"
            f"\\definecolor{{accentblue}}{{HTML}}{{{self.accent}}}\n"
            f"\\definecolor{{rowalt}}{{HTML}}{{{self.row_alt}}}\n"
            "\\pagecolor{backgroundcolor}\n"
            "\\color{textcolor}\n"
        )


DARK_THEME = Theme()


class Document:
    """Build a complete LaTeX document and compile to PDF."""

    # Each entry is either "pkg" or ("pkg", "options")
    PACKAGES = [
        "graphicx",
        ("xcolor", "table"),
        "geometry",
        "booktabs",
        "longtable",
        "hyperref",
        ("inputenc", "utf8"),
        "array",
        "ragged2e",
    ]

    def __init__(
        self,
        title: str,
        author: str = "TheBundle",
        landscape: bool = True,
        theme: Theme | None = None,
        margin: str = "0.75in",
    ):
        self.title = title
        self.author = author
        self.landscape = landscape
        self.theme = theme or DARK_THEME
        self.margin = margin
        self._sections: list[Section] = []
        self._extra_preamble: list[str] = []

    @staticmethod
    def _render_package(pkg) -> str:
        if isinstance(pkg, tuple):
            name, opts = pkg
            return f"\\usepackage[{opts}]{{{name}}}\n"
        return f"\\usepackage{{{pkg}}}\n"

    def add_preamble(self, latex_str: str):
        self._extra_preamble.append(latex_str)

    def add_section(self, section: Section):
        self._sections.append(section)

    def render(self) -> str:
        doc_class = "\\documentclass[landscape]{article}" if self.landscape else "\\documentclass{article}"
        orientation = "landscape, " if self.landscape else ""
        lines = [
            doc_class + "\n",
            *[self._render_package(p) for p in self.PACKAGES],
            f"\\geometry{{{orientation}margin={self.margin}}}\n",
            self.theme.preamble(),
            *self._extra_preamble,
            "\\begin{document}\n",
            f"\\title{{\\color{{textcolor}}{self.title}}}\n",
            f"\\author{{{self.author}}}\n",
            "\\maketitle\n",
            "\\tableofcontents\n",
            "\\newpage\n",
        ]
        for section in self._sections:
            lines.append(section.render())
        lines.append("\\end{document}\n")
        return "".join(lines)

    def build_pdf(self) -> bytes:
        """Compile the document to PDF bytes."""
        content = self.render()
        pdf = latex_lib.build_pdf(content)
        return bytes(pdf)

    def save_pdf(self, output_path: Path):
        """Compile and save the document to a PDF file."""
        content = self.render()
        pdf = latex_lib.build_pdf(content)
        pdf.save_to(str(output_path))
