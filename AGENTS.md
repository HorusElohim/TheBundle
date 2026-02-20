# Repository Guidelines

## Project Structure & Module Organization
- `src/bundle/` is the main Python package; subpackages are organized by feature area.
- `tests/` holds pytest suites and example modules.
- `references/` stores golden data used by tests; update only when intentionally regenerating reference outputs.
- `src/bundle/website/vendor/excalidraw/` is vendored third-party code, and `src/bundle/website/pages/*/static/` contains built assets.

## Build, Test, and Development Commands
- `pip install -e ".[test]"` installs the project with test tooling.
- `pip install -e ".[website]"` installs optional web dependencies.
- `pytest` runs the suite; use `pytest tests/pybind -k pkgconfig` to scope to a module.
- `python -m build` builds sdist/wheel artifacts for distribution.

## Core Modeling & Observability
- Use `bundle.core.data.Data` for any model that needs consistent metadata serialization/deserialization (JSON, schema, validation). Example: `class Job(data.Data): id: str; payload: dict`.
- Use `bundle.core.entity.Entity` when lifecycle and identity matter (creation time, age, unique IDs); it integrates with the core logger for start/stop style traces.
- Configure logging with `bundle.core.logger.setup_root_logger(...)` and retrieve scoped loggers via `logger.get_logger(__name__)`. Pair with `bundle.core.tracer` when you need call-level tracing across sync/async code.
- `Data.from_dict` and `Data.as_dict` are traced at `VERBOSE` level; keep high-volume serialization logs at verbose, not debug/info.
- For `@data.model_validator(mode="after")`, use instance methods (`self`) rather than class-style signatures.

## Core Logging
- Use `bundle.core.logger` as the canonical logging API (`setup_root_logger`, `get_logger`).
- Default runtime logs should stay practical: `DEBUG` for development, `INFO` for normal operation, `VERBOSE` only when deep tracing is required.
- Avoid `print` for runtime behavior; use structured logger calls so output remains filterable and test-friendly.
- Keep exception logging explicit with context; use tracer exception levels rather than duplicating stack traces manually.

## Core Tracing
- Use `bundle.core.tracer.Sync/Async` wrappers and decorators for call-level instrumentation.
- Prefer decorator form for stable APIs and wrapper form for one-off calls.
- Use `call_raise` when failure should propagate; use `call` only when tuple `(result, exception)` handling is needed.
- Set `log_level`/`exc_log_level` intentionally for noisy paths (for example serialization or streaming loops).

## Core Sockets
- Use `bundle.core.sockets` abstractions for ZeroMQ patterns instead of ad hoc socket wrappers.
- Keep socket config explicit in the model (`type`, `mode`, `endpoint`) and validated through `Data` fields.
- Prefer async send/recv flows and tracer wrappers for observability in long-running socket tasks.
- Keep protocol payloads typed (`Data`) where possible; avoid raw dict contracts spread across modules.

## Core Platform
- Use `bundle.core.platform.Platform` and related helpers for environment/process introspection.
- Avoid duplicating OS/python/runtime detection logic; centralize it in `platform.py`.
- Keep platform-specific behavior isolated behind platform helpers, not scattered in feature code.

## Core Utils
- Use `bundle.core.utils` for shared helpers (path, duration, generic utility behavior) before introducing new local helpers.
- If a helper is reused across modules, promote it to `core.utils`; if it is feature-specific, keep it local and minimal.
- Do not add convenience wrappers without a clear reduction in duplication.

## Bundle CLI
- Top-level CLI entrypoint is `src/bundle/cli.py` (`bundle` command group via `rich_click`).
- Feature CLIs (`website`, `ble`, `youtube`, `pybind`, `testing`, `scraper`) should remain thin adapters over core services.
- CLI commands should validate inputs early and delegate business logic to reusable modules, not embed heavy logic in command functions.
- Keep CLI output consistent with logger/tracer strategy; avoid mixed style output unless interactive UX explicitly requires it.

## Website Architecture (Consolidated)
- Use the names `pages` and `components` only. Do not re-introduce `sections/widgets` aliases or compatibility hacks.
- Components are page-scoped: instantiate them in the page module and attach routes with `components.attach_routes(router, *COMPONENTS)`.
- Do not maintain global component activation/registration for runtime behavior.
- Each component is atomic and folder-local:
  - `component.py` (primary `Data` class)
  - `template.html`
  - `frontend/` assets
- Prefer inheritance over duplication:
  - common websocket behavior belongs in `components/websocket/base/`
  - child components override only what is unique (typically `handle_websocket`).
- Keep websocket route creation centralized via base `create_router(...)`.
- Use typed websocket payloads in `components/websocket/base/messages.py` (`Data` models + ser/des helpers).
- Keep message dispatch logic in `components/websocket/base/message_router.py`.
- Use composable websocket runtime blocks from base backend (`run_websocket`, `every`, `drain_text`, `receive_json`) instead of ad hoc loops.
- Keep code minimal and explicit:
  - no speculative abstractions
  - no duplicate route declarations
  - no dead helpers left from previous designs.

## Coding Vibes
- First rule: less code for the same result is always better.
- Optimize for elegant minimalism: less code, fewer moving parts, clearer intent.
- Prefer small composable building blocks over large monolithic implementations.
- Keep abstractions only when they remove real duplication or unlock reuse; avoid “abstraction for abstraction”.
- Inheritance is valid when behavior is truly shared; overrides should stay tiny and purpose-specific.
- Every new line should justify its existence (readability, correctness, reuse, or testability).
- Favor explicit, typed contracts (`Data` models, clear method boundaries) over implicit dict-based behavior.
- Keep APIs concise and modern: predictable names, narrow signatures, zero compatibility hacks unless explicitly requested.
- Refactors should trend toward simpler architecture, not broader architecture.
- When in doubt, choose the solution that is:
  - easier to read
  - easier to test
  - easier to delete or evolve later
  - and uses the fewest concepts possible.

## Coding Style & Naming Conventions
- Use 4-space indentation and target Python 3.10+.
- Format with Black (line length 128) and sort imports with isort (line length 120, `__init__.py` skipped).
- Flake8 max line length is 128; keep lint warnings to zero.
- Naming: modules `snake_case.py`, classes `CamelCase`, constants `UPPER_SNAKE_CASE`, tests `test_*.py`.
- For frontend static assets, treat `.ts` as source of truth: never edit built `.js` files directly; make changes in `.ts` and rebuild outputs.

## Testing Guidelines
- Frameworks: `pytest` with `pytest-asyncio`; doctests are enabled via `--doctest-modules`.
- New tests should live under `tests/` and follow `test_*` function naming.
- If a change affects reference data, update the corresponding files under `references/` as part of the same PR.
- For website websocket changes, run at least `pytest tests/website -q`.
- Preserve page-scoped routing guarantees in tests (only attached component routes should exist on a page router).

## Commit & Pull Request Guidelines
- Commit messages use an emoji prefix plus a short imperative summary (for example `:sparkles: add BLE bundle module`, `:adhesive_bandage: fix deprecation warning`).
- PRs should include: a clear description, test results, and linked issues; add screenshots for website/UI changes.
- Note any vendored or generated asset updates explicitly in the PR description.
