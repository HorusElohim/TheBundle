# bundle.docs

Sphinx-based documentation builder integrated with TheBundle CLI.

## CLI Commands

```bash
# Build HTML documentation for the current project
bundle docs build

# Build docs for a specific project with custom output
bundle docs build --source /path/to/project --output /path/to/output

# Serve built docs locally
bundle docs serve --port 8000

# Initialize persistent Sphinx config files
bundle docs init
```

## Features

- **Auto-discovery**: Reads `pyproject.toml` to detect project name, version, author, and package layout
- **MyST Markdown**: Uses `myst-parser` so existing README.md files are included directly
- **Static API analysis**: Uses `sphinx-autoapi` to generate API docs from source without importing modules
- **Ephemeral staging**: Generates `conf.py` and `index.md` at build time — no permanent Sphinx files to maintain
- **External repo support**: Build docs for any Python project with `--source`

## Dependencies

Install with:

```bash
pip install thebundle[docs]
```

Requires: `sphinx`, `furo`, `myst-parser`, `sphinx-autoapi`
