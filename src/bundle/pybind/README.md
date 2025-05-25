# TheBundle Pybind Subpackage

The `bundle.pybind` subpackage provides a modern, declarative, and extensible framework for building, configuring, and managing C++/pybind11 extension modules in Python projects. It enables seamless integration with `setuptools`, `pyproject.toml`, and system-level build tools such as CMake and pkg-config.

---

## Key Features

- **Declarative configuration**: Define all extension modules, sources, and build options in `pyproject.toml` under `[tool.pybind11]`.
- **Automatic pkg-config integration**: Resolve compiler and linker flags for dependencies using `pkg-config`, including custom search paths.
- **CMake support**: Utilities for configuring and building CMake-based C++ projects, with platform-specific flags.
- **Async-first resolution**: All resolution and build steps are async, enabling parallel builds and responsive CLI tools.
- **Plugin architecture**: Easily extend or modify build and resolution logic via plugin hooks.
- **Rich CLI**: Manage builds and inspect configuration with a modern, user-friendly CLI.
- **Cross-platform**: Handles platform-specific quirks for Windows, Linux, and macOS.
- **First-class setuptools integration**: Generate `Extension` objects and custom `build_ext` commands for use in `setup.py`.

---

## Quickstart

### 1. Project Structure

```
your_project/
├── bindings/
│   └── python/
│       └── example_module/
│           ├── shape_bindings.cpp
│           └── geometry_bindings.cpp
├── ...
├── pyproject.toml
└── setup.py

```

### 2. pyproject.toml Example

```toml
[build-system]
requires = ["setuptools", "wheel", "setuptools_scm", "thebundle"]
build-backend = "setuptools.build_meta"

[project]
name = "realpkg"
# ...

[tool.setuptools.packages.find]
where = ["bindings/python"]

[tool.pybind11]

# shape submodule
[[tool.pybind11.modules]]
name = "example_module.shape"
sources = ["bindings/python/example_module/shape_bindings.cpp"]
pkgconfig = { packages = ["example_module"], extra_dirs = [] }
extra_compile_args = ["-O3"]
extra_link_args = []

# geometry submodule
[[tool.pybind11.modules]]
name = "example_module.geometry"
sources = ["bindings/python/example_module/geometry_bindings.cpp"]
pkgconfig = { packages = ["example_module"], extra_dirs = [] }
extra_compile_args = ["-O3"]
extra_link_args = []
```

### 3. setup.py Example

```python
from bundle.pybind import Pybind

Pybind.setup(__file__)
```

---

## How It Works

### Declarative Specs

- **ProjectSpec**: Root object, loaded from `[tool.pybind11]` in `pyproject.toml`.
- **ModuleSpec**: Each extension module is described with its name, sources, language, compiler/linker flags, and pkg-config dependencies.
- **PkgConfigSpec**: Describes dependencies to be resolved via `pkg-config`.

### Resolution Pipeline

1. **Spec Loading**: `Pybind` loads and validates the project/module specs from `pyproject.toml`.
2. **Pkg-config Resolution**: For each module, dependencies are resolved using `pkg-config`, collecting include/library dirs and flags.
3. **Module Resolution**: Combines user-specified and resolved flags, sources, and options into a `ModuleResolved` object.
4. **Extension Generation**: Each `ModuleResolved` is converted into a `setuptools.Extension` for building.
5. **Build**: Extensions are built in-place using the custom `build_ext` command.

### Plugin System

- **PybindPluginSpec**: Apply transformations or checks to module specs before resolution.
- **PybindPluginResolved**: Modify or inspect resolved modules before extension generation.
- Register plugins via the `plugins` argument to `Pybind` or in your own build scripts.

---

## CLI Usage

The CLI is available as `python -m bundle.pybind.cli` or via a custom entrypoint.

### Build Extensions

```sh
python -m bundle pybind build --path .
```

- Builds all pybind11 extensions in-place.
- Supports parallel builds with `--parallel`.

### Show Project Info

```sh
python -m bundle pybind info --path .
```

- Prints the resolved configuration for all modules.

---

## API Overview

### Main Entrypoint

```python
from bundle.pybind import Pybind

# In setup.py
Pybind.setup(__file__)
```

Programmatic usage


```python

pyb = Pybind("pyproject.toml")
resolved = await pyb.resolve()
extensions = await pyb.get_spec_extensions()
```

### Extension Generation

- `ExtensionSpec.from_module_resolved(module: ModuleResolved) -> Extension`
- Custom `build_ext` command for per-extension temp dirs and platform safety.

### CMake Utilities

- `CMakeService.configure(...)`: Configure a CMake project with platform-specific flags.
- `CMakeService.build(...)`: Build a CMake project or target.

### Pkg-config Utilities

- `PkgConfigService.resolve(spec: PkgConfigSpec)`: Resolve all flags for a dependency.

---

## Advanced Features

- **Platform Awareness**: Handles macOS deployment targets, Windows/Unix flags, and architecture-specific options.
- **Async Resolution**: All resolution and build steps are async, enabling fast, parallel builds.
- **Reference Data**: All resolved specs and build artifacts can be serialized for inspection or debugging.
- **Extensible**: Add custom plugins to modify specs or resolved modules for advanced workflows.

---

## Example: Adding a New Extension Module

Add a new module entry in `pyproject.toml`:

```toml
[[tool.pybind11.modules]]
name = "example_module.newfeature"
sources = ["bindings/python/example_module/newfeature_bindings.cpp"]
pkgconfig = { packages = ["example_module"], extra_dirs = [] }
extra_compile_args = ["-O3"]
extra_link_args = []
```

No changes to `setup.py` are needed—just re-run your build.

---

## Reference

### Specs

- **ProjectSpec**: Root config, holds all modules.
- **ModuleSpec**: Module name, sources, language, cpp_std, pkgconfig, extra_compile_args, extra_link_args.
- **PkgConfigSpec**: packages, extra_dirs.

### Services

- **PkgConfigService**: Resolves compiler/linker flags via pkg-config.
- **CMakeService**: Runs CMake configure/build commands.

### Resolvers

- **PkgConfigResolver**: Async resolver for pkg-config specs.
- **ModuleResolver**: Resolves a module spec to a resolved module.
- **ProjectResolver**: Resolves the whole project.

### Plugins

- **PybindPluginSpec**: Pre-resolution spec plugin interface.
- **PybindPluginResolved**: Post-resolution plugin interface.

---

## Best Practices

- Keep all extension configuration in `pyproject.toml` for reproducibility.
- Use pkg-config for all C++ dependencies to ensure portability.
- Use plugins for custom build logic or validation.
- Prefer async workflows for large projects or CI pipelines.

---

## See Also

- [pybind11 documentation](https://pybind11.readthedocs.io/)
- [setuptools documentation](https://setuptools.pypa.io/)
- [pkg-config documentation](https://www.freedesktop.org/wiki/Software/pkg-config/)
- [CMake documentation](https://cmake.org/)

---

For further details, consult the inline documentation in each module and the example project in `tests/pybind/example_module`.
