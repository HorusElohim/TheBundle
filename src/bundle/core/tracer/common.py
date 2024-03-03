from .. import logger
from typing import TypeVar, ParamSpec

log = logger.get_logger(__name__)

P, R = ParamSpec("P"), TypeVar("R")


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
    return str(callable_obj)


def log_call_success(func, args, kwargs, result, stacklevel):
    log.debug(
        "%s  %s.%s(%s, %s) -> %s",
        log.Emoji.success,
        func.__module__,
        get_callable_name(func),
        args,
        kwargs,
        result,
        stacklevel=stacklevel,
    )


def log_call_exception(func, args, kwargs, exception, stacklevel):
    log.error(
        "%s  %s.%s(%s, %s). Exception: %s",
        log.Emoji.failed,
        func.__module__,
        get_callable_name(func),
        args,
        kwargs,
        exception,
        exc_info=True,
        stacklevel=stacklevel,
    )


def log_cancelled_exception(func, args, kwargs, exception, stacklevel):
    log.warning(
        "%s  %s.%s(%s, %s) -> async cancel exception: %s",
        logger.Emoji.warning,
        func.__module__,
        get_callable_name(func),
        args,
        kwargs,
        exception,
        exc_info=False,
        stacklevel=stacklevel - 1,
    )
