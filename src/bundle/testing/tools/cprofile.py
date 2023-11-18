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


import time
import logging
from pathlib import Path
from functools import wraps
import cProfile

LOGGER = logging.getLogger(__name__)


# Setting default values for expected duration and performance threshold in nanoseconds
EXPECTATION_INIT_NS = 0
EXPECTATION_EXCESS_NS = 1_000_000_00  # 10 ms


def cprofile_decorator(
    expected_duration: int = EXPECTATION_INIT_NS,
    performance_threshold: int = EXPECTATION_EXCESS_NS,
    cprofile_dump_dir: Path | None = None,
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwds):
            # Enable profiling
            LOGGER.debug(f"profiling {func.__name__} ...")
            pr = cProfile.Profile()
            pr.enable()

            # Record start time in nanoseconds
            start_ns = time.perf_counter_ns()

            # Execute the wrapped function
            result = func(*args, **kwds)

            # Stop profiling
            pr.disable()

            # Record end time in nanoseconds
            end_ns = time.perf_counter_ns()

            # Calculate elapsed time in nanoseconds
            elapsed_ns = end_ns - start_ns

            # Compare against expected duration and threshold in nanoseconds
            duration_diff_ns = abs(elapsed_ns - expected_duration)

            # Debug message with actual duration, expected duration, and the difference
            LOGGER.debug(
                f"Function {func.__name__} finished execution in {elapsed_ns}ns. "
                f"Expected duration was {expected_duration}ns. "
                f"Difference: {duration_diff_ns}ns."
            )

            if elapsed_ns > expected_duration:
                LOGGER.warning(
                    f"Function {func.__name__} took {elapsed_ns}ns, "
                    f"{duration_diff_ns}ns longer than the expected={expected_duration}ns."
                )
            if duration_diff_ns > performance_threshold:
                LOGGER.error(
                    f"Function {func.__name__} exceeded the performance threshold by "
                    f"{duration_diff_ns - performance_threshold}ns."
                )

            # Dump stats if a directory is provided
            if cprofile_dump_dir:
                dump_file = cprofile_dump_dir / f"{func.__name__}.{type(result).__name__}.prof"
                LOGGER.debug(f"Dumping cProfile stats to: {dump_file}")
                pr.dump_stats(str(dump_file))

            # Return the function's result
            return result

        return wrapper

    return decorator
