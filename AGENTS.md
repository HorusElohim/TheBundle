# Repository Guidelines

## Project Structure & Module Organization
Source lives in `src/bundle`, split into targeted subpackages: `core` (runtime primitives), `pybind` (C++ bridges), `scraper`, `testing`, `website`, and `youtube`. `src/bundle/cli.py` wires the dynamic `bundle` CLI, importing subcommand modules (`pybind`, `scraper`, `testing`, `website`, `youtube`). Tests mirror that layout (`tests/core`, `tests/pybind`) with global fixtures in `tests/conftest.py`. Golden artifacts reside under `references/<platform>/ref`; keep sibling `failed` directories empty.

## Build, Test, and Development Commands
Bootstrap a venv (`python -m venv venv`), activate it (`source venv/bin/activate` on POSIX, `./venv/Scripts/Activate.ps1` on Windows), then install extras via `python -m pip install -e .[all]`. The CLI exposes helpers such as `bundle --help`, `bundle version`, and `bundle testing python pytest`. The test command accepts flags like `--no-logs`, `--no-cprof`, and `-s`; running plain `pytest` remains valid. Build wheels with `python -m build` and publish using `python -m twine upload dist/*` when the `pypi` extra is installed.

## Coding Style & Naming Conventions
Target Python 3.10+. Format with Black (line length 128) and isort (Black profile); lint with Flake8 (140-character cap, complexity ≤30). Follow snake_case for modules/functions, CapWords for classes, and UPPER_CASE for constants. Annotate new code, leaning on `typing_extensions` when backporting modern typing features.

## Testing Guidelines
Place tests beside their runtime counterparts (`tests/core/test_browser.py` for `bundle.core.browser`). Name tests descriptively (`test_feature_condition_expected_result`). Async tests rely on `pytest-asyncio` with function-scoped loops, and doctests run automatically (`--doctest-modules`). Serialization suites should reuse `bundle.testing.tools.decorators.data` for dict/JSON round-trips and schema validation, stacking `bundle.testing.tools.decorators.cprofile` when profiling output should land under `references/<platform>/cprofile`. When references change, refresh only the `ref` snapshots and leave `failed` directories untracked.

## Library Usage Patterns
Configure logging with `bundle.core.logger.setup_root_logger` (e.g., `log = setup_root_logger(level=Level.INFO, colored_output=True)`) to unlock custom levels such as `log.testing`. Model domain data by subclassing `bundle.core.data.Data`; use `await MyData.from_json(path)` and `await instance.dump_json(path)` for canonical I/O, and surface schemas via `await MyData.as_jsonschema()`. Wrap helpers with `bundle.core.tracer.Sync.decorator.call_raise` or the async variant to emit success/error telemetry automatically; tests can apply the same decorators while relying on CLI toggles to mute logs in CI.

## Commit & Pull Request Guidelines
Commits follow gitmoji conventions (`:adhesive_bandage: fix process decoding`, `:recycle: refactor tracer logging`). Use the Rust gitmoji CLI (`gitmoji -c`) to scaffold messages and keep history uniform. Group related edits per commit, reference issues when available, and provide PR descriptions covering motivation, test evidence (`bundle testing python pytest` or `pytest` output), and CLI/UI impacts. Confirm GitHub Actions status (Ubuntu, macOS, Windows, auto-reference update) before requesting review.