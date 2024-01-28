# Copyright 2023 HorusElohim

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


import logging
import json
import time
from typing import Any, Dict
from pathlib import Path


class Emoji:
    born = "❤️"
    success = "✅"
    failed = "❌"
    dead = "💀"

    @classmethod
    def status(cls, val: bool) -> str:
        return cls.success if val else cls.failed


LOGGING_LEVEL = logging.DEBUG

# Optional: Import colorama or similar library for colored output
from colorama import Fore, Style


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "time": time.strftime("%Y-%m-%d-%H:%M:%S", time.gmtime(record.created)),
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
    """
    Custom logging handler that outputs colored logs to the console.
    """

    COLORS = {
        "WARNING": Fore.YELLOW,
        "INFO": Fore.GREEN,
        "DEBUG": Fore.LIGHTMAGENTA_EX,
        "CRITICAL": Fore.RED,
        "ERROR": Fore.RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, Fore.WHITE)
        if record.levelname == "INFO":
            format_str = f"{color}%(levelname)-8s {Style.RESET_ALL}%(message)s"
        else:
            level_name = f"{color}%(levelname)-8s"
            target_name = f"{Fore.MAGENTA}%(name)s\t{Fore.BLACK}%(pathname)s:%(lineno)d:{Fore.WHITE}%(funcName)s "
            format_str = f"{level_name} {target_name}{Style.RESET_ALL} {color}%(message)s{Style.RESET_ALL}"
        formatter = logging.Formatter(format_str)
        return formatter.format(record)


def setup_logging(
    level=LOGGING_LEVEL, log_path: Path | None = None, colored_output=True, to_json=False, name: str | None = None
):
    """
    Set up logging with both file and console handlers.
    """

    # Logger setup
    logger_name = name if name else "bundle"
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if log_path:
        log_path.mkdir(parents=True, exist_ok=True)
        log_file = log_path / f"bundle-{time.strftime('%y.%m.%d.%H.%M.%S')}.json"

        # File handler with JSON formatting
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        # Format
        if to_json:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s [%(name)s] %(filename)s:%(funcName)s:%(lineno)d: %(message)s"
            )

        file_handler.setFormatter(formatter)
        file_handler.encoding = "utf-8"
        # Add File Handler
        logger.addHandler(file_handler)

    # Console handler with optional colored output
    console_handler = ColoredConsoleHandler()
    console_handler.encoding = "utf-8"
    if not colored_output:
        console_handler.setFormatter(logging.Formatter("%(levelname)s- [%(name)s]: %(message)s"))

    # Add Console Handler
    logger.addHandler(console_handler)
    # Propagate
    logger.propagate = False

    return logger
