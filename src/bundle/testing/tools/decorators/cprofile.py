import cProfile
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar

from .... import core
from .. import utils

logger = core.logger.get_logger(__name__)

EXPECTED_DURATION_NS = 100_000_000  # 100 ms
PERFORMANCE_THRESHOLD_NS = 100_000_000  # 100 ms
ENABLED = True

R = TypeVar("R")


class _ProfileContext:
    """
    Context manager to conditionally activate cProfile.
    When profiling is disabled, acts as a no-op.
    """

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled
        self.profiler: cProfile.Profile | None = cProfile.Profile() if enabled else None

    def __enter__(self) -> cProfile.Profile | None:
        if self.profiler:
            self.profiler.enable()
        return self.profiler

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.profiler:
            self.profiler.disable()


def cprofile(
    expected_duration: int = EXPECTED_DURATION_NS,
    performance_threshold: int = PERFORMANCE_THRESHOLD_NS,
    cprofile_folder: Path | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # If profiling is disabled, return the original function without modification.
        if not ENABLED:
            return func

        @wraps(func)
        async def wrapper(*args: Any, **kwds: Any) -> Any:
            logger.testing(f"[{func.__name__}] profiling async function ...")
            # Enclose the timing and dump logic in the profiling context.
            with _ProfileContext(ENABLED) as pr:
                start_ns = time.perf_counter_ns()
                result: Any = None
                exception: Exception | None = None
                try:
                    result = await func(*args, **kwds)
                except Exception as e:
                    exception = e
                end_ns = time.perf_counter_ns()
                elapsed_ns = end_ns - start_ns

                # Dump cProfile stats if a folder is provided.
                if cprofile_folder and pr is not None:
                    result_identifier = utils.class_instance_name(result) if result else "result"
                    dump_file = cprofile_folder / f"{func.__name__}.{result_identifier}.prof"
                    logger.testing(f"[{func.__name__}] dumping cProfile stats to: {dump_file}")
                    pr.dump_stats(str(dump_file))

                # Log performance details.
                logger.testing(f"[{func.__name__}] executed in {core.utils.format_duration_ns(elapsed_ns)}")
                duration_diff_ns = elapsed_ns - expected_duration
                if elapsed_ns > expected_duration and duration_diff_ns > performance_threshold:
                    logger.warning(
                        f"Function {func.__name__} exceeded the expected duration by "
                        f"{core.utils.format_duration_ns(duration_diff_ns)}. "
                        f"Actual duration: {core.utils.format_duration_ns(elapsed_ns)}, "
                        f"Expected duration: {core.utils.format_duration_ns(expected_duration)}."
                    )

            if exception is not None:
                raise exception
            return result

        return wrapper

    return decorator
