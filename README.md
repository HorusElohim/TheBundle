[![ubuntu 🐧](https://github.com/HorusElohim/TheBundle/actions/workflows/python-ubuntu.yml/badge.svg?branch=main)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-ubuntu.yml)
[![macos 🍏](https://github.com/HorusElohim/TheBundle/actions/workflows/python-darwin.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-darwin.yml)
[![windows 🪟](https://github.com/HorusElohim/TheBundle/actions/workflows/python-windows.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/python-windows.yml)
[![PyPI Release 🐍](https://github.com/HorusElohim/TheBundle/actions/workflows/publish-pypi.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/publish-pypi.yml)
[![auto reference update 🔄](https://github.com/HorusElohim/TheBundle/actions/workflows/auto-reference-update.yml/badge.svg)](https://github.com/HorusElohim/TheBundle/actions/workflows/auto-reference-update.yml)

# THE BUNDLE

![The Bundle Dream](thebundle.png)


## Overview

Welcome to **TheBundle** 🧯, a robust Python framework designed to simplify complex operations, from data management to browser automation.

### Features
- 🔢 Advanced data validation and lifecycle-managed entities.
- ⚙️ Asynchronous process execution and file downloading.
- 🌐 Simplified browser automation with Playwright.
- 📜 Enhanced logging with JSON and colored output.
- 🔄 ZeroMQ socket communication support.

### Core Modules

#### 1. [Logger](src/bundle/core/logger.py) 📜
Custom logging framework with colored console output, JSON formatting, and support for enhanced log levels.

#### 2. [Tracer](src/bundle/core/tracer/README.md) 📊
Unified tracing for asynchronous and synchronous operations with detailed logging and error handling.

#### 3. [Data](src/bundle/core/data.py) 🔢
Advanced JSON handling and validation with support for serialization and schema generation.

#### 4. [Entity](src/bundle/core/entity.py) 🔢
Lifecycle-managed objects extending `Data`, including features like unique identifiers and introspection.

#### 5. [Process](src/bundle/core/process.py) ⚙️
Execute shell commands asynchronously, stream outputs, and handle errors effectively.

#### 6. [Downloader](src/bundle/core/downloader.py) 🔣
Async file downloading with support for in-memory buffering and TQDM progress visualization.

#### 7. [Socket](src/bundle/core/socket.py) 🪟
ZeroMQ-based sockets with support for multiple communication patterns and chainable configurations.

#### 8. [Browser](src/bundle/core/browser.py) 🌐
Simplified Playwright integration for browser automation and testing.

#### 9. [Utils](src/bundle/core/utils.py) 🔧
Essential utilities for path management, duration formatting, and more.

### Installation

```bash
pip install thebundle
```

### Documentation

Refer to the [core modules documentation](src/bundle/core/README.md) for detailed information about individual components and their usage.

## 📜 License
Open-sourced under the [Apache-2.0 License](LICENSE).

---