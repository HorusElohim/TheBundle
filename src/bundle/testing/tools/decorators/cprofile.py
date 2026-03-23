# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from __future__ import annotations

import cProfile
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Optional

from .... import core
from .. import utils

log = core.logger.get_logger(__name__)

ENABLED: bool = False
EXPECTED_DURATION_NS: int = 100_000_000  # 100 ms
PERFORMANCE_THRESHOLD_NS: int = 100_000_000  # 100 ms


def get_cprofile_enabled() -> bool:
    return ENABLED


def set_cprofile_enabled(value: bool) -> None:
    global ENABLED
    ENABLED = value


class ProfileContext:
    """
    Context manager that profiles an async function execution,
    logs execution time, dumps stats, and warns if performance thresholds are exceeded.
    """

    def __init__(
        self,
        expected_duration: int,
        performance_threshold: int,
        cprofile_folder: Path | None,
        func_name: str,
        result_identifier: Callable[[Any], str],
    ) -> None:
        self.expected_duration = expected_duration
        self.performance_threshold = performance_threshold
        self.cprofile_folder = cprofile_folder
        self.func_name = func_name
        self.result_identifier = result_identifier
        self.profiler = cProfile.Profile()
        self.start_ns: int | None = None
        self.elapsed_ns: int | None = None
        self.result: Any = None

    def __enter__(self) -> ProfileContext:
        self.profiler.enable()
        self.start_ns = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.profiler.disable()
        end_ns = time.perf_counter_ns()
        self.elapsed_ns = end_ns - self.start_ns  # type: ignore
        formatted_elapsed = core.utils.format_duration_ns(self.elapsed_ns)
        log.testing(f"[{self.func_name}] executed in {formatted_elapsed}")

        if self.cprofile_folder:
            identifier = (
                self.result_identifier(self.result)
                if self.result is not None
                else "result"
            )
            dump_file = self.cprofile_folder / f"{self.func_name}.{identifier}.prof"
            log.testing(f"[{self.func_name}] dumping cProfile stats to: {dump_file}")
            self.profiler.dump_stats(str(dump_file))

        if self.elapsed_ns > self.expected_duration:
            diff_ns = self.elapsed_ns - self.expected_duration
            if diff_ns > self.performance_threshold:
                log.warning(
                    f"Function {self.func_name} exceeded the expected duration by "
                    f"{core.utils.format_duration_ns(diff_ns)}. "
                    f"Actual duration: {formatted_elapsed}, "
                    f"Expected duration: {core.utils.format_duration_ns(self.expected_duration)}."
                )


def cprofile(
    expected_duration: int = EXPECTED_DURATION_NS,
    performance_threshold: int = PERFORMANCE_THRESHOLD_NS,
    cprofile_folder: Path | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Check the flag dynamically at import time.
        if not get_cprofile_enabled():
            return func

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Check the flag dynamically at runtime.
            if not get_cprofile_enabled():
                return await func(*args, **kwargs)

            log.testing(f"[{func.__name__}] profiling async function ...")
            error: Exception | None = None
            result: Any = None

            with ProfileContext(
                expected_duration,
                performance_threshold,
                cprofile_folder,
                func.__name__,
                utils.class_instance_name,
            ) as ctx:
                try:
                    result = await func(*args, **kwargs)
                    ctx.result = result
                except Exception as exc:
                    error = exc

            if error is not None:
                raise error
            return result

        return wrapper

    return decorator
