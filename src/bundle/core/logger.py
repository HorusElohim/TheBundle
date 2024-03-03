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
from pathlib import Path
from typing import cast
from enum import IntEnum

from colorama import Fore, Style


class Emoji:
    """Emojis for logging status representation."""

    born = "🔵"
    dead = "🟣"

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
    TESTING = 5
    VERBOSE = 7
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    FATAL = CRITICAL


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


class ColoredConsoleHandler(logging.StreamHandler):
    """Custom logging handler for colored console output."""

    COLORS = {
        "WARNING": Fore.YELLOW,
        "INFO": Fore.GREEN,
        "DEBUG": Fore.LIGHTMAGENTA_EX,
        "CRITICAL": Fore.RED,
        "ERROR": Fore.RED,
        "VERBOSE": Fore.LIGHTBLACK_EX,
        "TESTING": Fore.CYAN,
    }

    def __init__(self):
        super().__init__()
        self.formatters = {}

    def format(self, record: logging.LogRecord) -> str:
        if record.levelname not in self.formatters:
            color = self.COLORS.get(record.levelname, Fore.WHITE)
            format_str = (
                f"{Fore.LIGHTBLUE_EX}%(asctime)s {color}%(levelname)-8s {Fore.MAGENTA}%(name)s\t"
                f"{Fore.LIGHTBLACK_EX}%(pathname)s:%(lineno)d:{Fore.WHITE}%(funcName)s {color}%(message)s{Style.RESET_ALL}"
            )
            self.formatters[record.levelname] = logging.Formatter(format_str)
        formatter = self.formatters[record.levelname]
        return formatter.format(record)


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
    """Set up a console handler for logging."""
    console_handler = ColoredConsoleHandler()
    if not colored_output:
        console_handler.setFormatter(logging.Formatter("%(levelname)s - [%(name)s]: %(message)s"))
    return console_handler


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
if __name__ == "__main__":
    logger = setup_root_logger(colored_output=True, log_path=Path("./logs"), to_json=False)
    logger.verbose("This is a verbose message.")
    logger.testing("This is a testing message")
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning.")
    logger.error("This is an error.")
    logger.critical("This is critical.")
