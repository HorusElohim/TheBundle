# TheBundle Core Modules Guide

This document provides a comprehensive overview of the `bundle.core` modules, emphasizing their advanced features and professional integration capabilities. Designed for maintainability and extensibility, these modules are suitable for robust, production-grade Python projects.

---

## Modules Overview

### `logger` 🐛
A sophisticated and extensible logging framework tailored for modern Python applications.

- **Custom log levels**: Extend beyond standard logging with levels such as `testing` and `verbose` for granular control.
- **Colorful console output**: Instantly distinguish log severity using `colorama`-powered styling for enhanced readability.
- **Structured JSON logs**: Output logs in JSON format for seamless integration with log aggregation and analysis tools.
- **Flexible handlers**: Direct logs to console, files, or both, each with independent formatting and filtering.
- **Contextual logging**: Attach rich metadata to every log entry for improved traceability.
- **Root logger configuration**: Use `setup_root_logger` to configure the global logging behavior for your entire application, ensuring consistency and centralized control.

**Why use it?**  
Accelerate debugging, maintain clear and actionable logs, and integrate effortlessly with enterprise logging solutions.

**Usage:**
```python
from bundle.core import logger

# Set up the root logger for the entire application
logger.setup_root_logger(level="INFO", json_logs=True)

log = logger.get_logger("myapp")
log.testing("Testing mode enabled.")
log.verbose("Detailed info here.")
log.info("App started.")
log.error("Something went wrong!", extra={"user": "alice"})
```

---

### `tracer` 📊
A unified tracing and error-handling system supporting both synchronous and asynchronous paradigms, with seamless paradigm switching and comprehensive type hinting.

- **Automatic call tracing**: Log every function entry, exit, and exception for complete execution visibility.
- **Stack trace capture**: Instantly pinpoint error origins with detailed stack traces.
- **Universal decorators**: Apply tracing to any function or method with a single decorator, regardless of sync or async nature.
- **Paradigm switching**: Effortlessly convert synchronous functions to asynchronous (and vice versa) by simply changing the decorator or function call, without altering the function body.
- **Full type hint support**: Maintains and adapts type hints even when switching between sync and async paradigms, ensuring type safety and IDE support.
- **Customizable log levels**: Specify distinct log levels for normal execution and exception handling.
- **Consistent API**: Identical interface for both synchronous and asynchronous workflows.

**Why use it?**  
Achieve deep, maintainable observability and error resilience across your codebase, with minimal intrusion and maximum flexibility for future refactoring.

**Usage:**
```python
from bundle.core import tracer

# Synchronous tracing
@tracer.Sync.decorator.call_raise
def compute(x: int, y: int) -> int:
    return x + y

# Asynchronous tracing (can switch paradigm by changing decorator)
@tracer.Async.decorator.call_raise
async def fetch_data(url: str) -> dict:
    return await some_async_op(url)

# Paradigm switching example
# The same function can be traced as sync or async by changing the decorator,
# and type hints are preserved.

# now must be invoke with await 
@tracer.Async.decorator.call_raise
def compute(x: int, y: int) -> int:
    return x + y

# now must be invoke without await 
@tracer.Sync.decorator.call_raise
async def fetch_data(url: str) -> dict:
    return await some_async_op(url)
```

---

### `data` 💻
Robust, Pydantic-based data modeling and validation for reliable and maintainable data structures.

- **Type-safe models**: Define data schemas using Python type hints for clarity and correctness.
- **Automatic validation**: Instantly detect and reject invalid data at instantiation.
- **Effortless serialization**: Convert to and from JSON with a single method call.
- **JSON schema generation**: Automatically produce JSON schemas for API documentation and validation.
- **Custom validators**: Enforce complex business rules and invariants within your models.

**Why use it?**  
Eliminate data inconsistencies, streamline API development, and ensure data integrity throughout your application.

**Usage:**
```python
from bundle.core import data

class User(data.Data):
    name: str
    age: int

user = User(name="Alice", age=30)
print(user.json())
print(user.json_schema())
```

---

### `entity` 🫏️
Lifecycle-aware, uniquely identifiable data objects for advanced domain modeling.

- **Creation timestamp**: Precisely record the instantiation time of every object.
- **Age tracking**: Measure object lifetime in nanoseconds for auditing and monitoring.
- **Globally unique IDs**: Assigns a collision-resistant identifier to each entity.
- **Inheritance-ready**: Easily extend for complex domain models and business logic.

**Why use it?**  
Enable precise tracking, auditing, and management of domain entities in large-scale systems.

**Usage:**
```python
from bundle.core import entity

class Product(entity.Entity):
    name: str
    price: float

p = Product(name="Laptop", price=999.99)
print(f"ID: {p.id}, Age: {p.age} ns")
```

---

### `process` ⚙️
Comprehensive process execution and management for system commands, optimized for asynchronous workflows.

- **Async execution by default**: Designed for modern async applications; use with `@tracer.Sync` for synchronous environments.
- **Live output streaming**: Process stdout and stderr in real time, enabling responsive feedback and logging.
- **Detailed logging**: Every command, argument, and result is captured for full traceability.
- **Custom callbacks**: React to process output as it arrives for advanced automation scenarios.
- **Graceful process lifecycle**: Start, monitor, and terminate processes safely and predictably.

**Why use it?**  
Automate, monitor, and debug system commands with reliability and transparency, suitable for CI/CD, automation, and orchestration.

**Usage:**
```python
from bundle.core import process

async def run():
    proc = process.Process()
    result = await proc("ls -la")
    print(result.stdout)
```

---

### `downloader` ⬇️
High-performance, asynchronous file downloading with robust progress tracking and error handling.

- **Async downloads**: Non-blocking, efficient file transfers for modern applications.
- **Progress bars**: Visual feedback via TQDM for user-friendly monitoring.
- **Flexible destinations**: Save files to disk or in-memory buffers as needed.
- **Automatic retries**: Resilient against transient network failures.
- **Streaming support**: Efficiently handle large files without excessive memory usage.

**Why use it?**  
Download files reliably and efficiently, with real-time progress and robust error recovery for data pipelines and automation.

**Usage:**
```python
from bundle.core import downloader

dl = downloader.Downloader(url="https://example.com/file.zip", destination="file.zip")
await dl.download()
```

---

### `socket` ⚡
Modern, chainable ZeroMQ socket abstraction for scalable, distributed messaging.

- **Multiple socket types**: Support for REQ, REP, PUB, SUB, PAIR, and more.
- **Chainable configuration**: Fluent, readable socket setup for rapid prototyping and production.
- **Async message handling**: Awaitable send/receive methods for high-performance networking.
- **Built-in proxying**: Easily route messages between sockets for advanced topologies.
- **Automatic serialization**: Transmit Python objects directly, not just raw bytes.

**Why use it?**  
Build scalable, robust distributed systems and microservices with minimal code and maximum flexibility.

**Usage:**
```python
from bundle.core import socket

sock = socket.Socket.pair().bind("tcp://*:5555")
await sock.send(b"Hello, World!")
```

---

### `browser` 🌐
Streamlined, async browser automation built on Playwright for testing and scraping.

- **Headless or headed operation**: Choose the optimal mode for your use case.
- **Multi-browser support**: Seamlessly automate Chromium, Firefox, and WebKit.
- **Context and page management**: Isolate sessions and tabs for parallel testing.
- **Async API**: Fast, non-blocking automation for modern Python applications.
- **Integrated error handling**: Fail gracefully and log issues for robust automation.

**Why use it?**  
Automate testing, scraping, and web interactions with a clean, maintainable, and Pythonic interface.

**Usage:**
```python
from bundle.core import browser

async with browser.Browser.chromium(headless=True) as b:
    page = await b.new_page()
    await page.goto("https://example.com")
    print(await page.title())
```

---

### `utils` 🔧
A suite of essential utilities for everyday development tasks.

- **Human-friendly duration formatting**: Convert nanoseconds to readable strings for logs and reports.
- **Path utilities**: Validate, create, and manipulate filesystem paths safely.
- **Date/time helpers**: Format and parse timestamps with ease.
- **Miscellaneous tools**: A collection of reusable functions to reduce boilerplate and improve code clarity.

**Why use it?**  
Accelerate development and ensure code quality with proven, reusable utility functions.

**Usage:**
```python
from bundle.core import utils

duration = utils.format_duration_ns(123456789)
print(duration)  # e.g., '2m:3s:456ms:789μs'
```

