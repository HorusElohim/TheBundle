# Core Modules Documentation

This README provides an overview of the core modules in the `TheBundle` project, detailing their purpose and key functionalities.

## 🚀 Modules Overview

### 1. `logger` 🐛
The `logger` module is a custom logging framework with enhanced features like colored console output and JSON-based file logging.

**Features:**
- 🔧 Supports custom log levels.
- 🎨 Integration with `colorama` for styled output.
- 📂 JSON formatter for structured logging.

**Example Usage:**
```python
from bundle.core import from bundle.core import logger

logger = get_logger("example")
logger.testing("This is a testing message.")
logger.verbose("This is a verbose message.")
logger.info("This is an info message.")
logger.error("This is an error message.")
```

### 2. `tracer` 📊
The `tracer` module facilitates unified tracing for synchronous and asynchronous operations with detailed error handling and debugging tools.

**Features:**
- 🔎 Log success and failure of function calls.
- 📊 Automatically capture stack traces for debugging.
- 🔧 Decorators for seamless integration into functions and methods.

**Example Usage:**
```python
from bundle.core import tracer

async def my_function():
    await tracer.asyn.call_raise(some_async_function, arg1, arg2)

@tracer.asyn.decorator_call_raise
async def my_function_decorated():
    await ...
```

### 3. `data` 🔢
The `data` module provides advanced data handling capabilities for serialization, validation, and JSON schema generation.

**Features:**
- ✅ Robust Pydantic-based data validation.
- 🔄 Serialization to and from JSON.
- 📜 JSON schema generation.

**Example Usage:**
```python
from bundle.core import data

class User(data.Data):
    name: str
    age: int

user = User(name="Alice", age=30)
print(user.json())
print(user.json_schema())
```

### 4. `entity` 🪟
The `entity` module extends the `data` module, introducing lifecycle management for objects.

**Features:**
- ⏱️ Track creation time and age.
- 🔑 Identifier generation for unique instances.

**Example Usage:**
```python
from bundle.core import entity

class Product(entity.Entity):
    name: str
    price: float

product = Product(name="Laptop", price=999.99)
print(f"Product age: {product.age} ns")
```

### 5. `process` ⚙️
The `process` module handles synchronous and asynchronous execution of system commands.

**Features:**
- 🌐 Execute commands with detailed logging.
- 🔎 Stream stdout and stderr output with callbacks.
- 🔄 Handle process lifecycle management.

**Example Usage:**
```python
from bundle.core import process

async def run_command():
    my_process = process.Process()
    result = await my_process("ls -la")
    print(result.stdout)
```

### 6. `downloader` ⬇️
The `downloader` module provides asynchronous file downloading with progress tracking.

**Features:**
- 💾 Save files to disk or memory buffer.
- 📊 Visual progress tracking with TQDM.

**Example Usage:**
```python
from bundle.core import downloader

downloader = downloader.Downloader(url="https://example.com/file.zip", destination="file.zip")
await downloader.download()
```

### 7. `socket` 🪟
The `socket` module implements a simplified interface for ZeroMQ sockets, supporting various communication patterns.

**Features:**
- 🔗 Chainable configuration methods.
- 🔄 Support for multiple socket types (REQ, REP, PUB, SUB, etc.).
- 🔧 Built-in message handling and proxying.

**Example Usage:**
```python
from bundle.core import socket

my_socket = socket.Socket.pair().bind("tcp://*:5555")
await my_socket.send(b"Hello, World!")
```

### 8. `browser` 🌐
The `browser` module is a wrapper for Playwright, simplifying browser automation and testing.

**Features:**
- 🔅 Launch headless browsers (Chromium, Firefox, WebKit).
- 🗒 Create and manage contexts and pages.
- 🛡️ Streamlined error handling and logging.

**Example Usage:**
```python
from bundle.core import browser

async with browser.Browser.chromium(headless=True) as my_browser:
    page = await my_browser.new_page()
    await page.goto("https://example.com")
    print(await page.title())
```

### 9. `utils` 🔧
The `utils` module provides utility functions for date formatting, path handling, and more.

**Features:**
- ⏳ Duration formatting in human-readable units.
- 🔐 Path existence validation and creation.

**Example Usage:**
```python
from bundle.core import utils

duration = utils.format_duration_ns(123456789)
print(duration)  # Outputs: '2m:3s:456ms:789µs'
```

---

For a detailed breakdown of module capabilities and advanced configurations, refer to the respective module documentation.
