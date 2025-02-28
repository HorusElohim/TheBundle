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

import cProfile
import time
from functools import wraps
from pathlib import Path

from .... import core
from .. import utils

logger = core.logger.get_logger(__name__)

# Setting default values for expected duration and performance threshold in nanoseconds
EXPECTED_DURATION_NS = 100_000_000  # 100 ms
PERFORMANCE_THRESHOLD_NS = 100_000_000  # 100 ms
ENABLED = True


def cprofile(
    expected_duration: int = EXPECTED_DURATION_NS,
    performance_threshold: int = PERFORMANCE_THRESHOLD_NS,
    cprofile_folder: Path | None = None,
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwds):
            # Enable profiling
            logger.testing(f"[{func.__name__}] profiling async function ...")
            if ENABLED:
                pr = cProfile.Profile()
                pr.enable()

            # Record start time in nanoseconds
            start_ns = time.perf_counter_ns()
            result = None
            exception = None
            try:
                # Execute the wrapped async function
                result = await func(*args, **kwds)
            except Exception as e:
                exception = e
            finally:
                if ENABLED:
                    # Stop profiling
                    pr.disable()

                # Record end time in nanoseconds
                end_ns = time.perf_counter_ns()

                # Calculate elapsed time in nanoseconds
                elapsed_ns = end_ns - start_ns

                # Log execution time
                logger.testing(f"[{func.__name__}] executed in {core.utils.format_duration_ns(elapsed_ns)}")

                # Calculate the difference between elapsed time and expected duration
                duration_diff_ns = elapsed_ns - expected_duration

                # Compare against expected duration and threshold in nanoseconds
                if elapsed_ns > expected_duration and duration_diff_ns > performance_threshold:
                    logger.warning(
                        f"Function {func.__name__} exceeded the expected duration by "
                        f"{core.utils.format_duration_ns(duration_diff_ns)}. "
                        f"Actual duration: {core.utils.format_duration_ns(elapsed_ns)}, "
                        f"Expected duration: {core.utils.format_duration_ns(expected_duration)}."
                    )

                # Dump stats if a directory is provided
                if ENABLED and cprofile_folder:
                    # Ensure that `result` has a meaningful identifier
                    result_identifier = utils.class_instance_name(result) if result else "result"
                    dump_file = cprofile_folder / f"{func.__name__}.{result_identifier}.prof"
                    logger.testing(f"[{func.__name__}] dumping cProfile stats to: {dump_file}")
                    pr.dump_stats(str(dump_file))

            # Return the function's result outside the try-except-finally
            if exception is not None:
                raise exception

            return result

        return wrapper

    return decorator
