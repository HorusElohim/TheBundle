[![ubuntu 🐧](https://github.com/HorusElohim/TheBundle/actions/workflows/python-ubuntu.yml/badge.svg?branch=main)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-ubuntu.yml)
[![macos 🍏](https://github.com/HorusElohim/TheBundle/actions/workflows/python-darwin.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-darwin.yml)
[![windows 🪟](https://github.com/HorusElohim/TheBundle/actions/workflows/python-windows.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-windows.yml)
[![PyPI Release 🐍](https://github.com/HorusElohim/TheBundle/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/publish-pypi.yml)
[![auto reference update 🔄](https://github.com/HorusElohim/TheBundle/actions/workflows/auto-reference-update.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/auto-reference-update.yml)
[![docs 📖](https://github.com/HorusElohim/TheBundle/actions/workflows/deploy-docs.yml/badge.svg)](https://HorusElohim.github.io/TheBundle/)

![The Bundle Dream](https://raw.githubusercontent.com/HorusElohim/TheBundle/main/thebundle.gif)

# TheBundle

**TheBundle** is a modern, extensible Python framework for robust, maintainable, and high-performance software projects. It provides a suite of core modules for logging, tracing, data modeling, process management, ZeroMQ sockets, browser automation, and more—plus advanced testing and pybind11/C++ extension tooling.

**Install**:
```sh
pip install thebundle
```

## Bootstrap Wizard

From a fresh machine, use the wizard to install Docker (plus WSL2/NVIDIA setup where applicable), Git, Python, create a venv, and install `thebundle[all]`.

Linux/macOS:
```sh
sh -c "$(curl -fsSL https://raw.githubusercontent.com/HorusElohim/TheBundle/main/wizards/run.sh)"
```

Windows (PowerShell):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/HorusElohim/TheBundle/main/wizards/platforms/windows.ps1 | iex"
```


### Continuous Integration: Platforms & Python Versions

| Platform  | Python Versions  |
| --------- | ---------------- |
| 🐧 Ubuntu  | 3.10 3.11, 3.12 |
| 🍏 macOS   | 3.10, 3.11, 3.12 |
| 🪟 Windows | 3.10, 3.11, 3.12 |

## Documentation

Full API reference and module guides are published on **GitHub Pages**:
👉 **https://HorusElohim.github.io/TheBundle/**

The documentation is auto-generated with Sphinx from docstrings and module READMEs, and deployed on every push to `main` via the [Deploy Docs](https://github.com/HorusElohim/TheBundle/actions/workflows/deploy-docs.yml) workflow. To build locally:

```sh
pip install thebundle[docs]
bundle docs build
bundle docs serve
```

Module guides:
- [Core Modules Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/core/README.md)
- [Testing Module Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/testing/README.md)
- [Pybind Subpackage Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/pybind/README.md)
- [Website Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/website/README.md)
- [LaTeX Module Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/latex/README.md)
- [HDF5 Module Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/hdf5/README.md)
- [Tracy Profiler Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/tracy/README.md)
- [Performance Report Guide](https://github.com/HorusElohim/TheBundle/blob/main/src/bundle/perf_report/README.md)


## License

Licensed under the Apache License, Version 2.0. See [LICENSE](https://github.com/HorusElohim/TheBundle/blob/main/LICENSE) for details.
