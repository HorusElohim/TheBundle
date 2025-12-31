# Repository Guidelines

## Project Structure & Module Organization
- `src/bundle/` is the main Python package; subpackages are organized by feature area.
- `tests/` holds pytest suites and example modules.
- `references/` stores golden data used by tests; update only when intentionally regenerating reference outputs.
- `src/bundle/website/vendor/excalidraw/` is vendored third-party code, and `src/bundle/website/sections/*/static/` contains built assets.

## Build, Test, and Development Commands
- `pip install -e ".[test]"` installs the project with test tooling.
- `pip install -e ".[website]"` installs optional web dependencies.
- `pytest` runs the suite; use `pytest tests/pybind -k pkgconfig` to scope to a module.
- `python -m build` builds sdist/wheel artifacts for distribution.

## Core Modeling & Observability
- Use `bundle.core.data.Data` for any model that needs consistent metadata serialization/deserialization (JSON, schema, validation). Example: `class Job(data.Data): id: str; payload: dict`.
- Use `bundle.core.entity.Entity` when lifecycle and identity matter (creation time, age, unique IDs); it integrates with the core logger for start/stop style traces.
- Configure logging with `bundle.core.logger.setup_root_logger(...)` and retrieve scoped loggers via `logger.get_logger(__name__)`. Pair with `bundle.core.tracer` when you need call-level tracing across sync/async code.

## Extensibility & Registries
- Use the registries in `bundle.website` to add new web sections or widgets; keep routes and assets registered rather than wired ad hoc.
- Place widget templates under `templates/widgets/` and assets under `static/widgets/` so they can be discovered consistently.
- Prefer a headless core + thin UI adapters; keep shared logic in one module and WebSocket routes under `/ws/*` to avoid static mounts.

## Coding Style & Naming Conventions
- Use 4-space indentation and target Python 3.10+.
- Format with Black (line length 128) and sort imports with isort (line length 120, `__init__.py` skipped).
- Flake8 max line length is 128; keep lint warnings to zero.
- Naming: modules `snake_case.py`, classes `CamelCase`, constants `UPPER_SNAKE_CASE`, tests `test_*.py`.

## Testing Guidelines
- Frameworks: `pytest` with `pytest-asyncio`; doctests are enabled via `--doctest-modules`.
- New tests should live under `tests/` and follow `test_*` function naming.
- If a change affects reference data, update the corresponding files under `references/` as part of the same PR.

## Commit & Pull Request Guidelines
- Commit messages use an emoji prefix plus a short imperative summary (for example `✨ add BLE bundle module`, `🩹 fix deprecation warning`).
- PRs should include: a clear description, test results, and linked issues; add screenshots for website/UI changes.
- Note any vendored or generated asset updates explicitly in the PR description.
