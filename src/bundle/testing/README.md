# TheBundle Testing Module Guide

This document an overview of the `bundle.testing` module, focusing on its advanced decorator-based approach for robust, maintainable, and scalable testing in Python projects.

---

## Key Features

- **Decorator-first design**: Powerful decorators for profiling, data validation, and test orchestration, minimizing boilerplate and maximizing clarity.
- **Integrated profiling with cProfile**: The `@cprofile` decorator enables per-test performance profiling, automatic stats dumping, and threshold-based warnings.
- **Automated data validation**: The `@data` decorator orchestrates round-trip serialization, schema validation, and reference management for Pydantic models.
- **Async-first support**: All decorators and test flows are designed for asynchronous code, with seamless integration into `pytest-asyncio`.
- **Reference and artifact management**: Automatic creation and management of reference data, temporary directories, and profiling outputs.
- **Pytest marker integration**: Use `@pytest.mark.bundle_cprofile` and `@pytest.mark.bundle_data` to declaratively apply decorators and pass parameters from your test suite.
- **Comprehensive error logging**: All test steps are logged with detailed context, and errors are captured and written to disk for post-mortem analysis.
- **Minimal test code**: Write concise tests that focus on what matters—your data and logic—while the decorators handle the rest.


