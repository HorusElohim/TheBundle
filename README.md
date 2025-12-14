[![ubuntu 🐧](https://github.com/HorusElohim/TheBundle/actions/workflows/python-ubuntu.yml/badge.svg?branch=main)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-ubuntu.yml)
[![macos 🍏](https://github.com/HorusElohim/TheBundle/actions/workflows/python-darwin.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-darwin.yml)
[![windows 🪟](https://github.com/HorusElohim/TheBundle/actions/workflows/python-windows.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-windows.yml)
[![PyPI Release 🐍](https://github.com/HorusElohim/TheBundle/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/publish-pypi.yml)
[![auto reference update 🔄](https://github.com/HorusElohim/TheBundle/actions/workflows/auto-reference-update.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/auto-reference-update.yml)

![The Bundle Dream](thebundle.gif)

# TheBundle

**TheBundle** is a modern, extensible Python framework for robust, maintainable, and high-performance software projects. It provides a suite of core modules for logging, tracing, data modeling, process management, ZeroMQ sockets, browser automation, and more—plus advanced testing and pybind11/C++ extension tooling.

**Install**:
```sh
pip install thebundle
```

**Extras**:
- Website stack (FastAPI server plus section dependencies):
  ```sh
  pip install -e ".[website]"
  ```
- The `excalidraw` section serves a self-hosted Excalidraw bundle (React + assets) directly from the app’s static files; no external calls are needed to load the editor.
- Self-hosted Excalidraw source lives in `src/bundle/website/vendor/excalidraw` (tag `v0.18.0`, PWA disabled by default). Rebuild the static bundle with Node 18–22 using:
  ```sh
  YARN_IGNORE_ENGINES=1 corepack yarn --cwd src/bundle/website/vendor/excalidraw/excalidraw-app build:app
  rm -rf src/bundle/website/sections/excalibur/static/excalidraw-web
  cp -R src/bundle/website/vendor/excalidraw/excalidraw-app/build/* src/bundle/website/sections/excalibur/static/excalidraw-web/
  ```
  Set `VITE_APP_ENABLE_PWA=true` before the build if you need the service worker.

## Updating Excalidraw (self-hosted)
If you need to refresh the self-hosted editor:
1. Pull the submodule (or the forked clone) at `src/bundle/website/vendor/excalidraw` to the desired branch/tag, then `git submodule update --init --recursive` if applicable.
2. Build the app with Node 18–22 (engines warning can be ignored with `YARN_IGNORE_ENGINES=1`):
   ```sh
   YARN_IGNORE_ENGINES=1 corepack yarn --cwd src/bundle/website/vendor/excalidraw/excalidraw-app build:app
   ```
3. Replace the served assets:
   ```sh
   rm -rf src/bundle/website/sections/excalibur/static/excalidraw-web
   cp -R src/bundle/website/vendor/excalidraw/excalidraw-app/build/* src/bundle/website/sections/excalibur/static/excalidraw-web/
   ```
4. Restart the dev server and hard-reload `/excalidraw` to bypass any cached service workers.

### Continuous Integration: Platforms & Python Versions

| Platform  | Python Versions  |
| --------- | ---------------- |
| 🐧 Ubuntu  | 3.10 3.11, 3.12 |
| 🍏 macOS   | 3.10, 3.11, 3.12 |
| 🪟 Windows | 3.10, 3.11, 3.12 |

## Documentation
For more information, see the inline documentation in each module and the example projects in `tests/`.
- [Core Modules Guide](src/bundle/core/README.md)
- [Testing Module Guide](src/bundle/testing/README.md)
- [Pybind Subpackage Guide](src/bundle/pybind/README.md)


## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
