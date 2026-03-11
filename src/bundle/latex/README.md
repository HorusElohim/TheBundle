# bundle.latex

LaTeX document generation module. Provides building blocks to compose and compile PDF documents from Python.

## Public API

| Class / Function | Module | Description |
|---|---|---|
| `Document` | `document.py` | Full document builder (preamble, packages, theme, sections). Compiles to PDF via `pdflatex`. |
| `Section` | `elements.py` | Section/subsection container. Supports text, figures, and tables as child blocks. |
| `Table` | `elements.py` | `longtable`-based table with column definitions, alternating row colors, and multi-page support. |
| `Column` | `elements.py` | Column definition (header, alignment, optional fixed width). |
| `Figure` | `elements.py` | `\includegraphics` wrapper with optional caption. |
| `escape()` | `elements.py` | Escape special LaTeX characters (`_`, `#`, `%`, `&`, `$`, `{`, `}`) and Unicode symbols. |

## Usage

```python
from bundle.latex import Document, Section, Table, Figure, escape
from bundle.latex.elements import Column

doc = Document(title="My Report", landscape=True)

section = Section("Results")
section.add_text("Some description here.")
section.add_figure(Figure("/tmp/plot.png"))

table = Table(
    columns=[
        Column("Name", width="4cm", align="l"),
        Column("Value", align="r"),
    ],
    row_color_alt="rowalt",
)
table.add_row([escape("my_var"), "42"])
section.add_table(table)

doc.add_section(section)
doc.save_pdf("output.pdf")
```

## Theme

`Document` uses `DARK_THEME` by default (dark background, light text). Pass a custom `Theme` instance to override colors.

## Dependencies

- `latex` (Python package wrapping `pdflatex`)
- TeX Live (`texlive-latex-base`, `texlive-latex-extra`, `texlive-fonts-recommended`)
