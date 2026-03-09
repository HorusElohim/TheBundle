# Repository Guidelines

## Project Structure & Module Organization
- `src/bundle/` is the main Python package; subpackages are organized by feature area.
- `tests/` holds pytest suites and example modules.
- `references/` stores golden data used by tests; update only when intentionally regenerating reference outputs.
- `src/bundle/website/vendor/` contains vendored third-party code.

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

## Core Subsystems
- **Logging**: Use `bundle.core.logger` (`setup_root_logger`, `get_logger`). Levels: `DEBUG` for dev, `INFO` for normal, `VERBOSE` for deep tracing. Never use `print` for runtime behavior.
- **Tracing**: Use `bundle.core.tracer.Sync/Async` decorators/wrappers. Prefer decorator form for stable APIs. Use `call_raise` for propagation, `call` for tuple `(result, exception)` handling. Set `log_level`/`exc_log_level` intentionally on noisy paths.
- **Sockets**: Use `bundle.core.sockets` for ZeroMQ patterns. Keep config in `Data` fields, payloads typed, prefer async flows.
- **Platform**: Use `bundle.core.platform.Platform` for environment/process introspection. Centralize OS/runtime detection there.
- **Utils**: Use `bundle.core.utils` for shared helpers before introducing local ones. Promote reused helpers to `core.utils`.

## Bundle CLI
- Top-level CLI entrypoint is `src/bundle/cli.py` (`bundle` command group via `rich_click`); feature CLIs are loaded dynamically.
- Feature CLIs should remain thin adapters over core services; validate inputs early, delegate logic to reusable modules.
- Website: `bundle website install`, `bundle site start [name]`, `bundle site build [name]`.
- Pods: `bundle pods list|status|build|run|down|logs [pod_name]`.

## Website Architecture
- Layout: `website/core/` (framework), `website/builtin/` (built-in components), `website/sites/` (site implementations), `website/vendor/` (third-party).
- Sites use `SiteManifest` to register pages via `initialize_pages(app, [...])`.
- Pages use `PageModule(__file__, name=..., slug=..., ...)` to encapsulate router, logger, templates, and metadata.
- Components are page-scoped: instantiate in the page module, attach with `components.attach_routes(page.router, *COMPONENTS)`.
- Each component is atomic and folder-local: `component.py`, `template.html`, optional CSS/JS.
- Websocket components inherit from `builtin/components/websocket/base/`; child components override `handle_websocket`.
- Use typed payloads via `base/messages.py` and dispatch via `base/message_router.py`.
- Use composable runtime blocks from base backend (`run_websocket`, `every`, `drain_text`, `receive_json`).

## Pods
- `src/bundle/pods/` manages containerized services via Docker Compose.
- Each pod is a folder under `pods/pods/` containing a `docker-compose.yml` (required for discovery).
- CLI: `bundle pods list|status|build|run|down|logs [pod_name]`.
- Root path via `--pods-root` flag or `BUNDLE_PODS_ROOT` env var.

## Coding Vibes
- Less code for the same result is always better. Elegant minimalism: fewer moving parts, clearer intent.
- Small composable blocks over monoliths. Abstractions only when they remove real duplication.
- Favor explicit, typed contracts (`Data` models) over implicit dict-based behavior.
- Refactors should trend toward simpler, not broader, architecture.
- When in doubt: easier to read, easier to test, easier to delete, fewest concepts.

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
