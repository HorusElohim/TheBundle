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
            target_name = f"{Fore.MAGENTA}%(name)s:{Fore.WHITE}%(filename)s:%(lineno)d:{Fore.BLACK}%(funcName)s "
            format_str = f"{level_name} {target_name}{Style.RESET_ALL} {color}%(message)s{Style.RESET_ALL}"
        formatter = logging.Formatter(format_str)
        return formatter.format(record)


def setup_logging(
    log_path: Path = Path("logs"),
    log_level=logging.INFO,
    colored_output=True,
    to_json=False,
):
    """
    Set up logging with both file and console handlers.
    """
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / f"bundle-{time.strftime('%y.%m.%d.%H.%M.%S')}.json"

    # File handler with JSON formatting
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    # Format
    if to_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s.%(mssecs)03d - %(levelname)s - [%(name)s] - %(filename)s:%(funcName)s:%(lineno)d: - %(message)s"
        )

    file_handler.setFormatter(formatter)
    file_handler.encoding = "utf-8"

    # Console handler with optional colored output
    console_handler = ColoredConsoleHandler()
    console_handler.encoding = "utf-8"
    if not colored_output:
        console_handler.setFormatter(
            logging.Formatter("%(levelname)s- [%(name)s]: %(message)s")
        )

    # Logger setup
    logger = logging.getLogger("bundle")
    logger.setLevel(log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False
    
    return logger
