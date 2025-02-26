# Copyright 2024 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import json
import logging
import time
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Mapping, cast

from colorama import Fore, Style
from rich.logging import RichHandler  # Use Rich's handler for improved console output


def get_callable_name(callable_obj):
    """
    Helper function to retrieve the name of a callable for logging purposes.

    Args:
        callable_obj: The callable object whose name is to be retrieved.

    Returns:
        str: The qualified name of the callable.
    """
    if hasattr(callable_obj, "__qualname__"):
        return callable_obj.__qualname__
    elif hasattr(callable_obj, "__class__") and hasattr(callable_obj.__class__, "__qualname__"):
        return callable_obj.__class__.__qualname__
    elif hasattr(callable_obj, "__call__") and hasattr(callable_obj.__call__, "__qualname__"):
        return callable_obj.__call__.__qualname__
    return repr(callable_obj)


class Emoji:
    """Emojis for logging status representation."""

    start = "🔵"
    end = "🟣"

    success = "🟢"
    failed = "🔴"
    warning = "🟡"

    @classmethod
    def status(cls, val: bool) -> str:
        """Return the success or failed emoji based on a boolean value."""
        return cls.success if val else cls.failed


# Log Levels
class Level(IntEnum):
    NOTSET = 0
    EXPECTED_EXCEPTION = 3
    TESTING = 5
    VERBOSE = 7
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    FATAL = CRITICAL


logging.addLevelName(Level.EXPECTED_EXCEPTION, "EXPECTED_EXCEPTION")
logging.addLevelName(Level.TESTING, "TESTING")
logging.addLevelName(Level.VERBOSE, "VERBOSE")


DEFAULT_LOGGING = logging.DEBUG


class BundleLogger(logging.getLoggerClass()):
    Emoji = Emoji

    """Custom Logger with a verbose method."""

    def verbose(self, msg: str, *args, stacklevel=2, **kwargs) -> None:
        if self.isEnabledFor(Level.VERBOSE):
            self._log(Level.VERBOSE, msg, args, stacklevel=stacklevel, **kwargs)

    def testing(self, msg: str, *args, stacklevel=2, **kwargs) -> None:
        if self.isEnabledFor(Level.TESTING):
            self._log(Level.TESTING, msg, args, stacklevel=stacklevel, **kwargs)

    def callable_success(
        self,
        func: Callable[..., Any],
        args: Any,
        kwargs: Mapping[str, Any],
        result: Any,
        stacklevel: int = 2,
        level: Level = Level.DEBUG,
    ) -> None:
        """
        Log a successful call at the given logging level.

        Args:
            func: The callable that was executed.
            args: Positional arguments passed to the callable.
            kwargs: Keyword arguments passed to the callable.
            result: The result returned by the callable.
            stacklevel: The stack level for the log record.
            level: The logging level to use (default: DEBUG).
        """
        if self.isEnabledFor(level):
            self._log(
                level,
                "%s  %s.%s(%s, %s) -> %s",
                (Emoji.success, func.__module__, get_callable_name(func), args, kwargs, result),
                stacklevel=stacklevel,
            )

    def callable_exception(
        self,
        func: Callable[..., Any],
        args: Any,
        kwargs: Mapping[str, Any],
        exception: Exception,
        stacklevel: int = 2,
        level: Level = Level.ERROR,
    ) -> None:
        """
        Log an exception raised during a call at the given logging level.

        Args:
            func: The callable that raised the exception.
            args: Positional arguments passed to the callable.
            kwargs: Keyword arguments passed to the callable.
            exception: The exception that was raised.
            stacklevel: The stack level for the log record.
            level: The logging level to use (default: ERROR).
        """
        if self.isEnabledFor(level):
            self._log(
                level,
                "%s  %s.%s(%s, %s). Exception: %s",
                (Emoji.failed, func.__module__, get_callable_name(func), args, kwargs, exception),
                exc_info=True,
                stacklevel=stacklevel,
            )

    def callable_cancel(
        self,
        func: Callable[..., Any],
        args: Any,
        kwargs: Mapping[str, Any],
        exception: Exception,
        stacklevel: int = 2,
        level: Level = Level.WARNING,
    ) -> None:
        """
        Log a cancelled asynchronous call at the given logging level.

        Args:
            func: The callable that was cancelled.
            args: Positional arguments passed to the callable.
            kwargs: Keyword arguments passed to the callable.
            exception: The async cancel exception.
            stacklevel: The stack level for the log record.
            level: The logging level to use (default: WARNING).
        """
        if self.isEnabledFor(level):
            self._log(
                level,
                "%s  %s.%s(%s, %s) -> async cancel exception: %s",
                (Emoji.warning, func.__module__, get_callable_name(func), args, kwargs, exception),
                exc_info=True,
                stacklevel=stacklevel - 1,
            )


# Set BundleLogger as the default logger class
logging.setLoggerClass(BundleLogger)


def get_logger(name: str) -> BundleLogger:
    """Retrieve a logger with the correct type hint."""
    # BundleLogger is already set globally.
    logger = logging.getLogger(name)
    return cast(BundleLogger, logger)


class JsonFormatter(logging.Formatter):
    """Formatter for JSON-style log output."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "file": record.pathname,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


def setup_file_handler(log_path: Path, to_json: bool) -> logging.FileHandler:
    """Set up a file handler for logging."""
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Invalid log path: {log_path}") from e

    log_file = log_path / f"bundle-{time.strftime('%y.%m.%d.%H.%M.%S')}"
    log_file = log_file.with_suffix(".json" if to_json else ".log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    formatter = (
        JsonFormatter()
        if to_json
        else logging.Formatter("%(asctime)s - %(levelname)s [%(name)s] %(filename)s:%(funcName)s:%(lineno)d: %(message)s")
    )
    file_handler.setFormatter(formatter)
    return file_handler


def setup_console_handler(colored_output: bool) -> logging.StreamHandler:
    """
    Set up a console handler for logging.

    When colored_output is True, uses RichHandler with a custom Console that employs
    a custom Theme to style the custom TESTING and VERBOSE levels.
    """
    if colored_output:
        from rich.console import Console
        from rich.theme import Theme

        # Create a custom theme including styles for the custom levels.
        custom_theme = Theme(
            {
                "logging.level.debug": "bold magenta",
                "logging.level.info": "bold green",
                "logging.level.warning": "bold yellow",
                "logging.level.error": "bold red",
                "logging.level.critical": "bold red",
                "logging.level.testing": "bold cyan",
                "logging.level.verbose": "dim black",
            }
        )
        console = Console(theme=custom_theme)
        return RichHandler(console=console, rich_tracebacks=True)
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s - [%(name)s]: %(message)s"))
        return handler


def setup_root_logger(
    name: str | None = None,
    level: int = DEFAULT_LOGGING,
    log_path: Path | None = None,
    colored_output: bool = True,
    to_json: bool = False,
) -> BundleLogger:
    """
    Configure logging with optional file and console handlers.

    Args:
        name (str | None): Logger name. Defaults to "bundle".
        level (int): Logging level. Defaults to DEFAULT_LOGGING.
        log_path (Path | None): Path for log files. If None, skips file logging.
        colored_output (bool): Enable colored console output. Defaults to True.
        to_json (bool): Format log files as JSON if True. Defaults to False.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger_name = name if name else "bundle"
    logger = get_logger(logger_name)
    logger.setLevel(level)

    if log_path:
        file_handler = setup_file_handler(log_path, to_json)
        logger.addHandler(file_handler)

    console_handler = setup_console_handler(colored_output)
    logger.addHandler(console_handler)

    logger.propagate = False  # Prevent log duplication in root handlers
    return logger


# Example Usage
# Try me python logger.py
if __name__ == "__main__":
    import asyncio

    # -----------------------------------------------------------------------------
    # Setup Logger
    # -----------------------------------------------------------------------------
    logger = setup_root_logger(colored_output=True, log_path=Path("./logs"), to_json=True, level=Level.VERBOSE)

    # -----------------------------------------------------------------------------
    # Standard Logging Examples
    # -----------------------------------------------------------------------------
    logger.verbose("This is a verbose message.")
    logger.testing("This is a testing message.")
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning.")

    # -----------------------------------------------------------------------------
    # Callable Logging Examples
    # -----------------------------------------------------------------------------
    # Define a sample function.
    def sample_func(x, y):
        return x + y

    # Example: Log a successful callable execution.
    result = sample_func(3, 4)
    logger.callable_success(sample_func, (3, 4), {}, result, stacklevel=3)

    # -----------------------------------------------------------------------------
    # Exception Logging Examples
    # -----------------------------------------------------------------------------
    logger.info("------------------------ Exception Demo ------------------------")

    logger.critical("This is critical.")

    # Example: Log an exception during callable execution.
    try:
        raise ValueError("Sample exception")
    except Exception as exc:
        logger.callable_exception(sample_func, (3, 4), {}, exc, stacklevel=3)

    # Example: Log a cancelled asynchronous callable.
    try:
        raise asyncio.CancelledError("Sample cancelled exception")
    except asyncio.CancelledError as exc:
        logger.callable_cancel(sample_func, (3, 4), {}, exc, stacklevel=3)

    # Example: Log an exception.
    try:
        1 / 0
    except Exception as e:
        logger.error("This is an error with an exception.", exc_info=True)
